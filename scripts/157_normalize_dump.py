# 157_normalize_dump.py -- READ-ONLY: full text of "AIG - MR CC Normalize"
# so the missing-warehouse-CC patch (157b) can be written precisely.
import frappe


def log(*a):
    print(*a, flush=True)


row = frappe.db.get_value("Server Script", "AIG - MR CC Normalize",
                          ["name", "reference_doctype", "doctype_event",
                           "disabled", "script"], as_dict=True)
log(f"event={row.doctype_event} disabled={row.disabled} "
    f"ref={row.reference_doctype}")
log(row.script)
log("DONE 157")
