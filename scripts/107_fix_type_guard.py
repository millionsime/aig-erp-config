# 107_fix_type_guard.py -- The guard script did not fire (likely the
# RestrictedPython sandbox rejecting the set comprehension at runtime), and
# the failed probe left a stray Purchase-type draft. Repair: sandbox-safe
# guard body, verify it blocks, clean strays, re-verify transitions with the
# correct field name (next_state).

import frappe

COMPANY = "Adama Investment Group"
U = "enduser.agro@aig.local"


def log(*a):
    print(*a, flush=True)


log("STEP 1: sandbox-safe guard body")
GUARD = '''# AIG - End Users may only raise stock requests (Material Issue / Model 19).
# Purchase-type requests belong to Procurement; give a clear message instead
# of a silent workflow dead-end (no action button).
user = frappe.session.user
if user not in ("Administrator", "Guest"):
    roles = frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        fields=["role"],
    )
    role_names = []
    for r in roles:
        role_names.append(r.role)
    is_end_user = "AIG End User" in role_names
    is_power_user = (
        ("AIG Procurement Officer" in role_names)
        or ("AIG Inventory Administrator" in role_names)
        or ("AIG Main Store Administrator" in role_names)
        or ("System Manager" in role_names)
    )
    if is_end_user and not is_power_user:
        if doc.material_request_type != "Material Issue":
            frappe.throw(
                "End Users submit stock requests as 'Material Issue' (Model 19). "
                "Purchase-type requests are raised by a Procurement Officer."
            )'''

s = frappe.get_doc("Server Script", "AIG - MR End User Type Guard")
s.script = GUARD
s.enabled = 1
s.flags.ignore_permissions = True
s.save(ignore_permissions=True)
log("  guard rewritten (loops only, no comprehensions)")

log("")
log("STEP 2: clean stray probe drafts owned by the end user")
frappe.set_user("Administrator")
strays = frappe.get_all(
    "Material Request",
    filters={"owner": U, "docstatus": 0},
    fields=["name", "material_request_type"],
)
for m in strays:
    log(f"  deleting stray draft {m.name} (type={m.material_request_type})")
    frappe.delete_doc("Material Request", m.name, force=True, ignore_permissions=True)

log("")
log("STEP 3: VERIFY -- Purchase insert must now throw")
frappe.set_user(U)
blocked = False
msg = ""
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase",
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "items": [{"item_code": "AIG-INV-FEED", "qty": 1,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert(ignore_permissions=True)
except Exception:
    blocked = True
    tb = frappe.get_traceback().strip().splitlines()
    msg = next((ln for ln in reversed(tb) if "Material Issue" in ln or "End User" in ln), tb[-1])
log(f"  Purchase-type blocked: {blocked}")
log(f"  message: {msg[:160]}")

log("")
log("STEP 4: VERIFY -- Material Issue insert yields Submit Request -> Pending Store Review")
from frappe.model.workflow import get_transitions

probe_name = None
trans = []
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue",
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "aig_purpose_note": "probe (deleted)",
        "items": [{"item_code": "AIG-INV-FEED", "qty": 1,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert(ignore_permissions=True)
    probe_name = d.name
    ts = get_transitions(d)
    trans = [f"{t.action} -> {t.next_state}" for t in ts]
except Exception:
    log(f"  !! insert failed: {frappe.get_traceback().strip().splitlines()[-1]}")
log(f"  transitions: {trans}")

frappe.set_user("Administrator")
if probe_name:
    frappe.delete_doc("Material Request", probe_name, force=True, ignore_permissions=True)
    log(f"  cleaned probe {probe_name}")

log("")
ok = blocked and any("Submit Request" in t for t in trans)
log("VERDICT: " + ("FIXED" if ok else "!! still broken -- see above"))
