# 133d6_cc_scripts_dump.py -- READ-ONLY dump of CC normalize/default scripts.
import frappe


def log(*a):
    print(*a, flush=True)


for name in ["AIG - MR CC Normalize", "AIG - PO Cost Center Default",
             "AIG - CC Guard", "AIG - SE CC Intercept"]:
    if not frappe.db.exists("Server Script", name):
        log(f"--- {name}: MISSING ---")
        continue
    log(f"--- {name} ---")
    log(frappe.db.get_value("Server Script", name, "script") or "(empty)")
    log("")
log("READ-ONLY DUMP DONE")
