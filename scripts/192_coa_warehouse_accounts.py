# Run AFTER 191. Maps each warehouse to the stock account that matches it.
# Goods In Transit -> 13101 is a placeholder until finance names a transit account.
import frappe

company = "Adama Investment Group"

def acct(number):
    return frappe.db.get_value("Account", {"company": company, "account_number": number}, "name")

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
    else:
        print("no warehouse", w)

frappe.db.commit()
print("done")
