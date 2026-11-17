import frappe

company = "Adama Investment Group"
abbr = frappe.db.get_value("Company", company, "abbr")

def acct(number):
    return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")

want = {
    "default_inventory_account": "13103",   # Finished Goods (Stock type, leaf)
    "stock_adjustment_account": "50108",    # the account we just added
    "default_expense_account": "50101",     # first Cost of Goods Sold account
}
for field, num in want.items():
    name = acct(num)
    if name:
        frappe.db.set_value("Company", company, field, name)
        print("set", field, "=", name)
    else:
        print("MISSING account", num, "for", field)

# report which required stock accounts exist by type
for t in ["Stock", "Stock Adjustment", "Stock Received But Not Billed",
          "Expenses Included In Valuation", "Round Off", "Asset Received But Not Billed"]:
    rows = frappe.get_all("Account", filters={"company": company, "account_type": t, "is_group": 0}, pluck="name")
    print(t, "->", rows if rows else "NONE")

frappe.db.commit()
print("done")