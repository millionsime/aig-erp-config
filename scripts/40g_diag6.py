# AIG config - step 40g: print source of has_user_permission + call it directly.
import frappe
import inspect
import frappe.permissions as P

print("=== source: has_user_permission ===")
print(inspect.getsource(P.has_user_permission))

U = "enduser.agro@aig.local"
ABBR = "AIG"
DAIRY_CC = f"Dairy Farm - {ABBR}"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
ITEM = "AIG-INV-FEED"

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

print("\n=== direct has_user_permission call ===")
try:
    sig = inspect.signature(P.has_user_permission)
    print("signature:", sig)
except Exception:
    pass
try:
    r = P.has_user_permission(doc=mr, user=U, permtype="read")
    print("has_user_permission:", r)
except Exception:
    import traceback
    print(traceback.format_exc())

# show the link fields Frappe would consider for Cost Center on this doctype
print("\n=== meta get_link_fields / child CC values ===")
meta = frappe.get_meta("Material Request")
for df in meta.get_link_fields():
    print("parent link:", df.fieldname, "->", df.options, "value=", mr.get(df.fieldname))
print("item rows cost_center:", [i.get("cost_center") for i in mr.items])

frappe.set_user("Administrator")
frappe.delete_doc("Material Request", mr.name, ignore_permissions=True, force=True)
frappe.db.commit()
print("\nDONE")
