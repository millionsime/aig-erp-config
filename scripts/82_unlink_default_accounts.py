import frappe

company = "Adama Investment Group"

# 1. Clear the default accounts on Expense Claim Types
n = frappe.db.sql(
    "delete from `tabExpense Claim Account` where company=%s", company
)
print("Expense Claim Account rows cleared")

# 2. Report any other documents that still use a default account
accts = frappe.get_all("Account", filters={"company": company}, pluck="name")
checks = [
    ("Expense Claim Account", "default_account"),
    ("Salary Component Account", "account"),
    ("Mode of Payment Account", "default_account"),
    ("Payroll Entry", "payment_account"),
    ("Item Default", "expense_account"),
    ("Item Default", "income_account"),
]
for dt, field in checks:
    try:
        rows = frappe.get_all(dt, filters={field: ["in", accts]}, fields=["name", field], limit=20)
        if rows:
            print("STILL LINKED:", dt, field, len(rows), rows[:5])
    except Exception as e:
        print("skip", dt, field, e)

frappe.db.commit()
print("done")