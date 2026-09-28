# AIG foundation - BUILD F: Fixed Asset + Depreciation Cost Center inheritance test.
# This is the check the brief flagged as "explicitly confirmed, not assumed":
# create a CC-tagged fixed asset, run depreciation, and verify the auto-generated
# Accumulated Depreciation (Balance Sheet!) entry INHERITS the same Cost Center
# at both Journal Entry row level and GL Entry level.
from frappe.utils import add_months, today

COMPANY = "Adama Investment Group"
CC = "Dairy Farm - AIG"
CATEGORY = "Dairy Equipment"
ITEM = "AIG-TEST-MILK-CAN"
ASSET_NAME = "AIG CC TEST - Milk Can"

# 1. Asset Category with accounts + a 12-month straight-line finance book
if not frappe.db.exists("Asset Category", CATEGORY):
    cat = frappe.new_doc("Asset Category")
    cat.asset_category_name = CATEGORY
    cat.append("accounts", {
        "company_name": COMPANY,
        "fixed_asset_account": "Capital Equipment - AIG",
        "accumulated_depreciation_account": "Accumulated Depreciation - AIG",
        "depreciation_expense_account": "Depreciation - AIG",
        "capital_work_in_progress_account": "CWIP Account - AIG",
    })
    cat.append("finance_books", {
        "depreciation_method": "Straight Line",
        "total_number_of_depreciations": 12,
        "frequency_of_depreciation": 1,  # months between postings (1 = monthly)
    })
    cat.insert()
    print("CREATED Asset Category:", CATEGORY)
else:
    print("Asset Category exists:", CATEGORY)

# 2. Fixed-asset Item
if not frappe.db.exists("Item", ITEM):
    frappe.get_doc({
        "doctype": "Item",
        "item_code": ITEM,
        "item_name": "AIG CC Test Milk Can",
        "item_group": "Property & Fixed Assets",
        "stock_uom": "Nos",
        "is_stock_item": 0,
        "is_fixed_asset": 1,
        "asset_category": CATEGORY,
        "is_purchase_item": 1,
        "opening_stock": 0,
    }).insert()
    print("CREATED Item:", ITEM)
else:
    print("Item exists:", ITEM)

# 3. Clean up any previous test asset run
old = frappe.get_all("Asset", filters={"asset_name": ASSET_NAME}, pluck="name")
for name in old:
    a = frappe.get_doc("Asset", name)
    for je_name in frappe.get_all("Journal Entry", filters={"reference_name": name}, pluck="name"):
        je = frappe.get_doc("Journal Entry", je_name)
        if je.docstatus == 1:
            je.cancel()
        frappe.delete_doc("Journal Entry", je_name, force=True)
    if a.docstatus == 1:
        a.cancel()
    frappe.delete_doc("Asset", name, force=True)
    print("REMOVED previous test asset:", name)

# 4. The CC-tagged test asset
purchase_date = today()
LOCATION = frappe.db.get_value("Location", {"is_group": 0}, "name") \
    or frappe.db.get_value("Location", "Dairy Farm", "name") \
    or frappe.new_doc("Location").__class__ and None
if not LOCATION:
    loc = frappe.new_doc("Location")
    loc.location_name = "AIG Test Location"
    loc.insert()
    LOCATION = loc.name
asset = frappe.get_doc({
    "doctype": "Asset",
    "asset_name": ASSET_NAME,
    "item_code": ITEM,
    "company": COMPANY,
    "location": LOCATION,
    "purchase_date": purchase_date,
    "available_for_use_date": purchase_date,
    "gross_purchase_amount": 50000,
    "net_purchase_amount": 50000,
    "asset_quantity": 1,
    "cost_center": CC,                       # <-- the tag under test
    "calculate_depreciation": 1,
})
asset.append("finance_books", {
    "finance_book": None,
    "depreciation_method": "Straight Line",
    "total_number_of_depreciations": 12,
    "frequency_of_depreciation": 1,  # months between postings
    "depreciation_start_date": add_months(purchase_date, 1),
})
asset.insert()
# Depreciation posting only processes SUBMITTED assets (docstatus 1) whose
# Asset Depreciation Schedule is also submitted - submit both via the asset.
asset.submit()
frappe.db.commit()
asset_cost_center = frappe.db.get_value("Asset", asset.name, "cost_center")
print("CREATED Asset:", asset.name, "| cost_center =", asset_cost_center)
assert asset_cost_center == CC, "Asset did not retain its cost center!"

ads = frappe.db.get_value("Asset Depreciation Schedule",
                          {"asset": asset.name, "docstatus": 0 if True else 0}, "name")
print("Schedules for asset:", frappe.get_all("Asset Depreciation Schedule",
      filters={"asset": asset.name}, fields=["name", "docstatus"]))

# 5. Post depreciation due up to purchase_date + 1 month
from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries
post_depreciation_entries(add_months(purchase_date, 1))

# 6. THE EXPLICIT VERIFICATION
journals = frappe.get_all("Journal Entry", filters={"reference_name": asset.name},
                          fields=["name", "voucher_type", "docstatus", "posting_date"])
print("\nDepreciation Journals:", journals)
assert journals, "No depreciation Journal Entry was posted!"

for je in journals:
    rows = frappe.get_all("Journal Entry Account",
                          filters={"parent": je.name},
                          fields=["account", "cost_center", "debit", "credit"])
    print(f"\nJE {je.name} ({je.voucher_type}) rows:")
    ok_acc_dep = False
    for r in rows:
        print("   ", r)
        if r.account == "Accumulated Depreciation - AIG":
            ok_acc_dep = True
            assert r.cost_center == CC, (
                f"ACCUMULATED DEPRECIATION row lost the cost center! got={r.cost_center}")
    assert ok_acc_dep, "Accumulated Depreciation row missing from depreciation JE!"

    gls = frappe.get_all("GL Entry", filters={"voucher_no": je.name},
                         fields=["account", "cost_center", "debit", "credit"])
    print(f"GL entries for {je.name}:")
    for g in gls:
        print("   ", g)
        assert g.cost_center == CC, f"GL row for {g.account} posted WITHOUT cost center: {g.cost_center}"

print("\n*** PASS: depreciation entry inherits the asset's Cost Center on the")
print("*** Accumulated Depreciation (Balance Sheet) account, at JE and GL level.")
print("\nDONE-F")
