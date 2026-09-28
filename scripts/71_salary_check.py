# Read-only: exact account_name values.
for n in ["Salary - AIG", "Debtors - AIG", "Creditors - AIG"]:
    print(n, "->", frappe.db.get_value("Account", n, ["account_name", "account_type", "is_group"], as_dict=True))
print("company cost_center:", frappe.db.get_value("Company", "Adama Investment Group", "cost_center"))
print("DONE")
