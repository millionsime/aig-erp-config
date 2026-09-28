# 158_request_defaults_dump.py -- READ-ONLY: full text of
# "AIG - MR Request Defaults" (Before Insert) to understand how the header
# cost center gets pre-set (it pre-empts the 157b guard branch).
import frappe


def log(*a):
    print(*a, flush=True)


for name in ["AIG - MR Request Defaults"]:
    row = frappe.db.get_value("Server Script", name,
                              ["name", "reference_doctype", "doctype_event",
                               "disabled", "script"], as_dict=True)
    log(f"=== {name} ===")
    if not row:
        log("  NOT FOUND")
        continue
    log(f"  event={row.doctype_event} disabled={row.disabled}")
    log(row.script)
log("DONE 158")
