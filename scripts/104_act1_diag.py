# 104_act1_diag.py -- Read-only support for the Act-1 rehearsal questions:
# (1) what enduser.agro actually sees in Warehouse/Item lists server-side,
# (2) exact text of "AIG - MR Request Defaults" and "AIG - MR Approval Guard".

import frappe


def log(*a):
    print(*a, flush=True)


log("1) enduser.agro server-side list counts")
frappe.set_user("enduser.agro@aig.local")
for dt in ["Warehouse", "Item", "Cost Center", "Company"]:
    try:
        n = len(frappe.get_list(dt, limit=100))
        log(f"  {dt}: {n}")
    except Exception:
        log(f"  {dt}: FAIL {frappe.get_traceback().strip().splitlines()[-1][:80]}")
frappe.set_user("Administrator")

log("")
log("2) storeadmin.agro server-side list counts")
frappe.set_user("storeadmin.agro@aig.local")
for dt in ["Warehouse", "Material Request"]:
    try:
        n = len(frappe.get_list(dt, limit=100))
        log(f"  {dt}: {n}")
    except Exception:
        log(f"  {dt}: FAIL {frappe.get_traceback().strip().splitlines()[-1][:80]}")
frappe.set_user("Administrator")

log("")
log("3) AIG - MR Request Defaults (script text)")
log(frappe.db.get_value("Server Script", "AIG - MR Request Defaults", "script") or "(missing)")

log("")
log("4) AIG - MR Approval Guard (script text)")
log(frappe.db.get_value("Server Script", "AIG - MR Approval Guard", "script") or "(missing)")
