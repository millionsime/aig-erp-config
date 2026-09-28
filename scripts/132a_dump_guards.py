# 132a_dump_guards.py -- Dump PO/PE guard + three-way-match script bodies so
# the new committee/direct-tier gates align with existing raw-submit guards.

import frappe


def log(*a):
    print(*a, flush=True)


for name in ["AIG - PO Guard Raw Submit", "AIG - PE Guard Raw Submit",
             "AIG - Payment Three-Way Match", "AIG - PO Cost Center Default",
             "AIG - MR Approval Guard"]:
    if not frappe.db.exists("Server Script", name):
        log(f"--- {name}: MISSING ---")
        continue
    meta = frappe.db.get_value("Server Script", name,
                               ["script_type", "disabled"], as_dict=True)
    log(f"--- {name} {meta} ---")
    log(frappe.db.get_value("Server Script", name, "script") or "(empty)")
    log("")
