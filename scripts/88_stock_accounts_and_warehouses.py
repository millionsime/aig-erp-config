import frappe

company = "Adama Investment Group"

def acct(number):
    return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")

new = [
    ("Stock Received But Not Billed", "21607", "21600", "Stock Received But Not Billed", "Liability"),
    ("Asset Received But Not Billed", "21608", "21600", "Asset Received But Not Billed", "Liability"),
    ("Expenses Included In Valuation", "50109", "50000", "Expenses Included In Valuation", "Expense"),
]
for name, num, parent_num, atype, root in new:
    if acct(num):
        print("exists", num); continue
    d = frappe.new_doc("Account")
    d.update(dict(account_name=name, account_number=num, parent_account=acct(parent_num),
                  company=company, account_type=atype, root_type=root, is_group=0,
                  account_currency="ETB"))
    d.flags.ignore_permissions = True
    d.insert()
    print("created", d.name)

defaults = {
    "stock_received_but_not_billed": "21607",
    "asset_received_but_not_billed": "21608",
    "expenses_included_in_valuation": "50109",
    "capital_work_in_progress_account": "15108",
}
for field, num in defaults.items():
    frappe.db.set_value("Company", company, field, acct(num))
    print("company." + field, "=", acct(num))

wh = {
    "Work In Progress - AIG": "13102",
    "Finished Goods - AIG": "13103",
    "Stores - AIG": "13104",
    "Goods In Transit - AIG": "13101",
    "All Warehouses - AIG": "13104",
}
for w, num in wh.items():
    if frappe.db.exists("Warehouse", w):
        frappe.db.set_value("Warehouse", w, "account", acct(num))
        print("warehouse", w, "->", acct(num))

frappe.db.commit()
print("done")