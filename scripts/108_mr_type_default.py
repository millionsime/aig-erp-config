# 108_mr_type_default.py -- End Users still blocked: Material Request's system
# default type is "Purchase", and the quick-entry (+ Add) dialog never runs
# client scripts, so the Before-Validate guard refused the save. Fix:
#   1) Before Insert server script: for End-User-only users, convert the type
#      to "Material Issue" (transparent -- it is a system default, not intent).
#   2) Client script v2: override a pre-filled default and lock the field for
#      end users.
# Verify with a server-side insert that mimics quick entry (no client script).

import frappe

COMPANY = "Adama Investment Group"
U = "enduser.agro@aig.local"


def log(*a):
    print(*a, flush=True)


DEFAULT_SCRIPT = '''# AIG - End Users raise stock requests (Material Issue / Model 19). The
# Material Request form defaults to type "Purchase" and the quick-entry dialog
# bypasses client scripts, so convert the system default here, transparently.
# Purchase-type requests remain available to Procurement Officers.
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
            doc.material_request_type = "Material Issue"'''

log("STEP 1: Before Insert default script 'AIG - MR End User Type Default'")
if frappe.db.exists("Server Script", "AIG - MR End User Type Default"):
    s = frappe.get_doc("Server Script", "AIG - MR End User Type Default")
    s.script = DEFAULT_SCRIPT
    s.enabled = 1
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Server Script",
        "name": "AIG - MR End User Type Default",
        "script_type": "DocType Event",
        "doctype_event": "Before Insert",
        "reference_doctype": "Material Request",
        "enabled": 1,
        "script": DEFAULT_SCRIPT,
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("STEP 2: Client Script v2 (override default + lock field for end users)")
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
\t\t\tif (!is_end_user_only()) { return; }
\t\t\tfrm.set_df_property("material_request_type", "read_only", 1);
\t\t\tif (frm.is_new() && frm.doc.material_request_type !== "Material Issue") {
\t\t\t\tfrm.set_value("material_request_type", "Material Issue");
\t\t\t}
\t\t}
\t});
})();"""
name = "AIG - MR Default Type (End User)"
s = frappe.get_doc("Client Script", name)
s.script = CLIENT_JS
s.enabled = 1
s.flags.ignore_permissions = True
s.save(ignore_permissions=True)
log("  updated")

log("")
log("STEP 3: clear cache")
frappe.clear_cache()

log("")
log("STEP 4: VERIFY -- server-side insert mimicking quick entry (no client script)")
frappe.set_user(U)
probe = None
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase",   # the system default, as quick entry sends it
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "aig_purpose_note": "probe (deleted)",
        "items": [{"item_code": "AIG-INV-FEED", "qty": 1,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert()
    probe = d.name
    log(f"  insert OK: {d.name}, stored type = {d.material_request_type} (must be Material Issue)")
    from frappe.model.workflow import get_transitions
    ts = get_transitions(d)
    trans = [f"{t.action} -> {t.next_state}" for t in ts]
    log(f"  transitions: {trans}")
except Exception:
    log(f"  !! insert failed: {frappe.get_traceback().strip().splitlines()[-1]}")

frappe.set_user("Administrator")
if probe:
    frappe.delete_doc("Material Request", probe, force=True, ignore_permissions=True)
    log(f"  cleaned probe {probe}")

log("")
log("STEP 5: scripts now governing MR type for End Users")
for ss in ["AIG - MR End User Type Default", "AIG - MR End User Type Guard", "AIG - MR Request Defaults"]:
    dis = frappe.db.get_value("Server Script", ss, "disabled")
    log(f"  Server Script {ss}: {'enabled' if not dis else 'DISABLED'}")
en = frappe.db.get_value("Client Script", name, "enabled")
log(f"  Client Script {name}: {'enabled' if en else 'DISABLED'}")

log("")
log("DONE -- retry the request as the end user; type now self-corrects everywhere.")
