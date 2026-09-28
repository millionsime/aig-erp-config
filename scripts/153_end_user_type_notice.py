# 153_end_user_type_notice.py -- UX fix for the phase-1 End-User rule
# (commits on success). "AIG - MR End User Type Default" silently converts an
# End User's Material Request to 'Material Issue' - correct policy (end users
# raise stock requests only; purchases belong to Procurement) but invisible,
# which read like a bug in the demo ("I selected Purchase and it changed").
# The conversion now raises a visible info notice on save. Policy unchanged;
# idempotent.
import frappe


def log(*a):
    print(*a, flush=True)


SCRIPT = '''# AIG - End Users raise stock requests (Material Issue / Model 19). The
# Material Request form defaults to type "Purchase" and the quick-entry dialog
# bypasses client scripts, so convert the system default here - and SAY SO:
# the notice below makes the conversion visible on the form (policy unchanged:
# end users raise stock requests only; Purchase-type requests belong to
# Procurement Officers).
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
            doc.material_request_type = "Material Issue"
            frappe.msgprint(
                "AIG: your request was recorded as 'Material Issue' (Model 19 "
                "stock request). Purchase-type requests are raised by a "
                "Procurement Officer."
            )
'''

row = frappe.get_doc("Server Script", "AIG - MR End User Type Default")
row.script = SCRIPT
row.disabled = 0
row.flags.ignore_permissions = True
row.save(ignore_permissions=True)
log("AIG - MR End User Type Default updated: conversion now announces itself")

frappe.clear_cache()

log("")
log("verify 1: enduser creates with Purchase -> converted to Material Issue + notice")
ENDUSER = "enduser.agro@aig.local"
name = None
frappe.set_user(ENDUSER)
try:
    frappe.message_log = []
    d = frappe.get_doc({
        "doctype": "Material Request", "company": "Adama Investment Group",
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(),
        "aig_cost_center": "Animal Feed Factory - AIG",
        "aig_estimated_total": 900000,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 10, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 80000,
                   "warehouse": "Animal Feed Plant - AIG"}],
    })
    d.insert()
    name = d.name
    notice = any("Material Issue" in str(m.get("message"))
                 for m in (frappe.message_log or []))
finally:
    frappe.set_user("Administrator")
got = frappe.db.get_value("Material Request", name, "material_request_type")
log(f"  type in DB = {got!r}  notice shown = {notice}")
frappe.delete_doc("Material Request", name, force=True,
                  ignore_permissions=True)
log("  (probe doc deleted)")
if got != "Material Issue" or not notice:
    raise SystemExit("conversion/notice check FAILED")

log("")
log("verify 2: officer creates with Purchase -> stays Purchase")
OFFICER = "procurement.agro@aig.local"
frappe.set_user(OFFICER)
try:
    d2 = frappe.get_doc({
        "doctype": "Material Request", "company": "Adama Investment Group",
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(),
        "aig_cost_center": "Animal Feed Factory - AIG",
        "aig_estimated_total": 900000,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 10, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 80000,
                   "warehouse": "Animal Feed Plant - AIG"}],
    })
    d2.insert()
    name2 = d2.name
finally:
    frappe.set_user("Administrator")
got2 = frappe.db.get_value("Material Request", name2, "material_request_type")
log(f"  type in DB = {got2!r}")
frappe.delete_doc("Material Request", name2, force=True,
                  ignore_permissions=True)
log("  (probe doc deleted)")
if got2 != "Purchase":
    raise SystemExit("officer Purchase check FAILED")

log("")
log("field check: AIG Requested By on Material Request")
f = frappe.get_meta("Material Request").get_field("aig_requested_by")
log(f"  label={f.label!r} fieldtype={f.fieldtype!r} options={f.options!r}")
log("DONE 153")
