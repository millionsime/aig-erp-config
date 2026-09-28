# 133d7_majority_dump.py -- READ-ONLY dump of AIG - PO Committee Majority.
import frappe


def log(*a):
    print(*a, flush=True)


log(frappe.db.get_value("Server Script", "AIG - PO Committee Majority", "script"))
log("READ-ONLY DUMP DONE")
