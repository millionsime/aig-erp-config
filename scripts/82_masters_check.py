# 82_masters_check.py -- Read-only check of master counts after the purge,
# especially Item Group (a fully empty tree incl. root would block new Items)
# and Supplier. No changes.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("MASTERS CHECK (read-only)")

for dt in ("Item Group", "Item", "Supplier", "Customer", "Warehouse"):
    log(f"  {dt}: total {frappe.db.count(dt)}")

log("  Item Group rows:")
for name, par, is_group in frappe.get_all(
    "Item Group", fields=["name", "parent_item_group", "is_group"], as_list=True
):
    log(f"    - {name} (parent={par!r}, group={is_group})")

log("  Supplier rows:")
for name in frappe.get_all("Supplier", pluck="name"):
    log(f"    - {name}")

log("  Item rows:")
for name in frappe.get_all("Item", pluck="name"):
    log(f"    - {name}")

# Any submittable docs left anywhere for the company?
log("  Submittable leftovers for company (should be none):")
left = 0
for dt in [
    "Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry",
    "Journal Entry", "Stock Entry", "Material Request", "Sales Invoice",
    "Delivery Note", "Asset", "Asset Depreciation Schedule", "Asset Movement",
    "Budget", "Supplier Quotation", "Request for Quotation", "Quality Inspection",
]:
    if not frappe.db.table_exists(dt):
        continue
    cnt = frappe.db.count(dt, {"company": COMPANY})
    if cnt:
        left += cnt
        log(f"    !! {dt}: {cnt}")
if not left:
    log("    none -- all clear")
