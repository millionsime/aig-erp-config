import frappe
frappe.db.sql("delete from `tabMode of Payment Account` where company=%s", "Adama Investment Group")
frappe.db.commit()
print("mode of payment accounts cleared")
