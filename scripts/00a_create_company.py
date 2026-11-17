import frappe
frappe.set_user("Administrator")
frappe.db.set_value("Currency", "ETB", "enabled", 1)
if not frappe.db.exists("Company", "Adama Investment Group"):
    frappe.get_doc({"doctype": "Company", "company_name": "Adama Investment Group",
                    "abbr": "AIG", "default_currency": "ETB", "country": "Ethiopia"}).insert()
    frappe.db.commit()
print("companies:", frappe.get_all("Company", pluck="name"))
