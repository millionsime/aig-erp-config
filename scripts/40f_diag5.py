# AIG config - step 40f: use has_permission debug=True to reveal the denial reason.
import frappe
import inspect

U = "enduser.agro@aig.local"
ABBR = "AIG"
DAIRY_CC = f"Dairy Farm - {ABBR}"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
ITEM = "AIG-INV-FEED"

# locate the user-permission matching helper in frappe.permissions
import frappe.permissions as P
print("=== frappe.permissions members mentioning 'user' ===")
for nm in dir(P):
    if "user" in nm.lower():
        print(" ", nm)

frappe.set_user(U)
mr = frappe.get_doc({
    "doctype": "Material Request", "company": "Adama Investment Group",
    "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
    "aig_cost_center": DAIRY_CC,
    "items": [{"item_code": ITEM, "qty": 2, "warehouse": DAIRY_WH,
               "schedule_date": frappe.utils.today()}],
})
mr.insert()
frappe.db.commit()
print("\n=== has_permission read debug ===")
ok = frappe.has_permission("Material Request", ptype="read", doc=mr, throw=False, debug=True)
print("RESULT read:", ok)

frappe.set_user("Administrator")
frappe.delete_doc("Material Request", mr.name, ignore_permissions=True, force=True)
frappe.db.commit()
print("\nDONE")
