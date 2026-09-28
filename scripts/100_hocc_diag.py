# 100_hocc_diag.py -- Check (a) Warehouse.aig_cost_center population,
# (b) whether a Material Request row auto-carrying Head Office CC fails the
# same way for enduser.agro, (c) existing Client Scripts on SE/MR.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("1) Warehouse.aig_cost_center population")
meta_fields = {f.fieldname for f in frappe.get_meta("Warehouse").fields}
log(f"  custom field exists: {'aig_cost_center' in meta_fields}")
if "aig_cost_center" in meta_fields:
    for wh in frappe.get_all("Warehouse", fields=["name", "aig_cost_center"]):
        if not wh.aig_cost_center:
            log(f"    MISSING: {wh.name}")
    total = frappe.db.count("Warehouse", {"company": COMPANY})
    filled = frappe.db.count("Warehouse", {"company": COMPANY, "aig_cost_center": ("is", "set")})
    log(f"  filled: {filled}/{total}")

log("")
log("2) Material Request same trap? (enduser.agro, row CC = Head Office)")
U = "enduser.agro@aig.local"
for label, cc in [("row CC = Head Office - AIG", "Head Office - AIG"),
                  ("row CC = Dairy Farm - AIG", "Dairy Farm - AIG"),
                  ("row CC empty", None)]:
    frappe.set_user(U)
    doc = frappe.new_doc("Material Request")
    doc.company = COMPANY
    doc.material_request_type = "Material Issue"
    doc.schedule_date = frappe.utils.today()
    doc.aig_cost_center = cc or "Dairy Farm - AIG"
    doc.append("items", {"item_code": "AIG-INV-FEED", "qty": 1,
                         "warehouse": "Dairy Farm Store - AIG",
                         "schedule_date": frappe.utils.today(),
                         **({"cost_center": cc} if cc else {})})
    doc.name = "new-material-request-test0000"
    try:
        frappe.has_permission(doc, "read", user=U, throw=True)
        log(f"  {label}: READ OK")
    except Exception:
        log(f"  {label}: READ FAIL (PermissionError)")
frappe.set_user("Administrator")

log("")
log("3) existing Client Scripts on Stock Entry / Material Request")
for dt in ("Stock Entry", "Material Request"):
    rows = frappe.get_all("Client Script", filters={"dt": dt}, fields=["name", "enabled", "view"])
    log(f"  {dt}: {[ (r.name, r.enabled) for r in rows ]}")
