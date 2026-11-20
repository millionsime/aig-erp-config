# Run AFTER 83/84/86. Sets the stock-related company defaults and reports which
# account types exist (clears "Set default inventory account for perpetual inventory").
import frappe

company = "Adama Investment Group"

def acct(number):
    return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")

want = {
    "default_inventory_account": "13103",         # Finished Goods
    "stock_adjustment_account": "50108",          # Stock Adjustment
    "default_expense_account": "50101",           # Raw Materials Consumed
    "stock_received_but_not_billed": "21607",
    "asset_received_but_not_billed": "21608",
    "expenses_included_in_valuation": "50109",
    "capital_work_in_progress_account": "15108",
}
for field, num in want.items():
    name = acct(num)
    if name:
        frappe.db.set_value("Company", company, field, name)
        print("set", field, "=", name)
    else:
        print("MISSING account", num, "for", field)

for t in ["Stock", "Stock Adjustment", "Stock Received But Not Billed",
          "Expenses Included In Valuation", "Round Off", "Asset Received But Not Billed"]:
    rows = frappe.get_all("Account", filters={"company": company, "account_type": t, "is_group": 0}, pluck="name")
    print(t, "->", rows if rows else "NONE")

frappe.db.commit()
print("done")
