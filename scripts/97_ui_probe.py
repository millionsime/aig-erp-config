# 97_ui_probe.py -- Simulate what the UI does when enduser.agro /
# procurement.agro open a form: get_doc("Company", ...) (throws exactly the
# "No permission for Company ..." error if broken), list warehouses, and open
# the Material Request list. Read-only.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


CASES = ["enduser.agro@aig.local", "procurement.agro@aig.local", "head.agro@aig.local"]

for user in CASES:
    frappe.set_user(user)
    log(f"AS {user}")
    try:
        doc = frappe.get_doc("Company", COMPANY)  # the exact failing call
        log(f"  Company doc load: OK ({doc.company_name})")
    except Exception:
        log(f"  !! Company doc load FAILED: {frappe.get_traceback().strip().splitlines()[-1]}")
    try:
        whs = frappe.get_list("Warehouse", limit=3, pluck="name")
        log(f"  Warehouse list: OK ({len(whs)} rows, e.g. {whs[:2]})")
    except Exception:
        log(f"  !! Warehouse list FAILED: {frappe.get_traceback().strip().splitlines()[-1]}")
    try:
        mrs = frappe.get_list("Material Request", limit=3, pluck="name")
        log(f"  Material Request list: OK ({len(mrs)} rows)")
    except Exception:
        log(f"  !! Material Request list FAILED: {frappe.get_traceback().strip().splitlines()[-1]}")
    try:
        ccs = frappe.get_list("Cost Center", limit=10, pluck="name")
        log(f"  Cost Center list: OK ({len(ccs)} rows visible)")
    except Exception:
        log(f"  !! Cost Center list FAILED: {frappe.get_traceback().strip().splitlines()[-1]}")
    log("")

frappe.set_user("Administrator")
log("PROBE DONE")
