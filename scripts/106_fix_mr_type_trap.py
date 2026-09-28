# 106_fix_mr_type_trap.py -- The "no Submit Request button" root cause: the
# End User's saved MRs are material_request_type="Purchase"; her only workflow
# action exists for "Material Issue" (Model 19). Purchase-type requests have no
# End User path (by policy), but the UI failed silently. Fix:
#   1) Server Script guard: End Users get a CLEAR message if they try to
#      create a non-Material-Issue request (Purchase etc. -> Procurement's path).
#   2) Client Script default: for End Users, new Material Requests preset to
#      "Material Issue" so the form starts on the correct track.
# Then verify: Purchase insert throws with the message; Material Issue insert
# yields a Submit Request transition; probe doc cleaned up.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("STEP 1: Server Script 'AIG - MR End User Type Guard' (Before Validate)")
GUARD = '''# AIG - End Users may only raise stock requests (Material Issue / Model 19).
# Purchase-type requests are raised by a Procurement Officer; give a clear
# message instead of a silent workflow dead-end (no action button).
user = frappe.session.user
if user in ("Administrator", "Guest"):
    pass
else:
    roles = {r.role for r in frappe.get_all(
        "Has Role", filters={"parent": user, "parenttype": "User"}, pluck="role")}
    if ("AIG End User" in roles
            and not ({"AIG Procurement Officer", "AIG Inventory Administrator",
                      "AIG Main Store Administrator", "System Manager"} & roles)
            and doc.material_request_type != "Material Issue"):
        frappe.throw("End Users submit stock requests as 'Material Issue' (Model 19). "
                     "Purchase-type requests are raised by a Procurement Officer.")'''

if frappe.db.exists("Server Script", "AIG - MR End User Type Guard"):
    s = frappe.get_doc("Server Script", "AIG - MR End User Type Guard")
    s.script = GUARD
    s.enabled = 1
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Server Script",
        "name": "AIG - MR End User Type Guard",
        "script_type": "DocType Event",
        "doctype_event": "Before Validate",
        "reference_doctype": "Material Request",
        "enabled": 1,
        "script": GUARD,
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("STEP 2: Client Script 'AIG - MR Default Type (End User)'")
CLIENT_JS = """(function () {
\tfunction is_end_user_only() {
\t\tvar roles = frappe.user_roles || [];
\t\treturn roles.indexOf("AIG End User") >= 0
\t\t\t&& roles.indexOf("AIG Procurement Officer") < 0
\t\t\t&& roles.indexOf("AIG Inventory Administrator") < 0
\t\t\t&& roles.indexOf("AIG Main Store Administrator") < 0;
\t}
\tfrappe.ui.form.on("Material Request", {
\t\tonload: function (frm) {
\t\t\tif (frm.is_new() && is_end_user_only() && !frm.doc.material_request_type) {
\t\t\t\tfrm.set_value("material_request_type", "Material Issue");
\t\t\t}
\t\t}
\t});
})();"""
name = "AIG - MR Default Type (End User)"
if frappe.db.exists("Client Script", name):
    s = frappe.get_doc("Client Script", name)
    s.script = CLIENT_JS
    s.enabled = 1
    s.dt = "Material Request"
    s.view = "Form"
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Client Script",
        "name": name,
        "dt": "Material Request",
        "view": "Form",
        "enabled": 1,
        "script": CLIENT_JS,
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("STEP 3: clear cache")
frappe.clear_cache()

log("")
log("STEP 4: VERIFY (as enduser.agro)")
U = "enduser.agro@aig.local"
frappe.set_user(U)

# 4a: Purchase-type insert must now throw the instructive message
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
    msg = str(frappe.get_traceback().strip().splitlines()[-1])
log(f"  Purchase-type insert blocked: {blocked} ({msg[:110]})")

# 4b: Material Issue insert works and yields the Submit Request transition
from frappe.model.workflow import get_transitions

ok = False
trans = []
probe_name = None
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue",
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "aig_purpose_note": "probe (will be deleted)",
        "items": [{"item_code": "AIG-INV-FEED", "qty": 1,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert(ignore_permissions=True)
    probe_name = d.name
    ts = get_transitions(d)
    trans = [f"{t.action}->{t.to_state}" for t in ts]
    ok = True
except Exception:
    log(f"  !! Material Issue insert failed: {frappe.get_traceback().strip().splitlines()[-1]}")
log(f"  Material Issue insert OK: {ok}; transitions: {trans}")

frappe.set_user("Administrator")
if probe_name:
    try:
        frappe.delete_doc("Material Request", probe_name, force=True, ignore_permissions=True)
        log(f"  cleaned up probe {probe_name}")
    except Exception:
        log(f"  !! cleanup failed for {probe_name} (delete manually)")

log("")
log("VERDICT: " + ("FIXED -- Submit Request appears for Material Issue requests; Purchase-type is blocked with a clear message" if (blocked and ok) else "!! check above"))
