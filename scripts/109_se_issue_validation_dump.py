# 109_se_issue_validation_dump.py -- Read-only: dump the SE issue validation
# + raw submit guard scripts so the Act-4 (store keeper) instructions match
# the exact enforced fields. No changes.

import frappe


def log(*a):
    print(*a, flush=True)


for name in ["AIG - SE Issue Validation", "AIG - SE Guard Raw Submit"]:
    log(f"=== {name} ===")
    log(frappe.db.get_value("Server Script", name, "script") or "(missing)")
    log("")
