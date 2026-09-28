import frappe
print("AIG Custom DocPerm rows:", frappe.db.count("Custom DocPerm", {"role": ["like", "AIG%"]}))
print("DocPerm doctypes:", sorted([p for p in set(frappe.get_all("Custom DocPerm", filters={"role": ["like", "AIG%"]}, pluck="parent")) if p]))
print("Workflow State masters:", frappe.get_all("Workflow State", pluck="name"))
print("Workflow Action masters:", frappe.get_all("Workflow Action Master", pluck="name"))
print("CostCenters total:", frappe.db.count("Cost Center", {"company": "Adama Investment Group"}))
print("Items AIG:", frappe.get_all("Item", filters={"name": ["like", "AIG%"]}, pluck="name"))
print("Suppliers:", frappe.get_all("Supplier", filters={"supplier_group": "AIG Vendors"}, pluck="name"))
print("COUNTS_DONE")
