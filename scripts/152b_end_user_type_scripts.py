# 152b_end_user_type_scripts.py -- READ-ONLY dump of the two phase-1 scripts
# that police material_request_type on Material Request.
import frappe


def log(*a):
    print(*a, flush=True)


for name in ["AIG - MR End User Type Default", "AIG - MR End User Type Guard"]:
    row = frappe.db.get_value("Server Script", name,
                              ["name", "reference_doctype", "doctype_event",
                               "disabled", "script"], as_dict=True)
    log(f"=== {name} ===")
    if not row:
        log("  NOT FOUND")
        continue
    log(f"  event={row.doctype_event} disabled={row.disabled}")
    log(row.script)
    log("")
log("DONE 152b")
