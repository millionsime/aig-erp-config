# AIG config - step 40c: introspect the Cost Center user-permission match on MR.
import frappe
import traceback

ABBR = "AIG"
U_ENDUSER = "enduser.agro@aig.local"
DAIRY_CC = f"Dairy Farm - {ABBR}"
AGRO_CC = f"Agro - {ABBR}"

frappe.set_user(U_ENDUSER)
try:
    from frappe.permissions import get_user_permissions
    up = get_user_permissions(U_ENDUSER)
    print("=== user permissions (enduser.agro) ===")
    for k, v in up.items():
        print(k, "->", [ (x.get("value"), x.get("applicable_for")) for x in v ])
except Exception:
    print("get_user_permissions err:")
    print(traceback.format_exc())

print("\n=== Cost Center link fields on Material Request meta ===")
meta = frappe.get_meta("Material Request")
for df in meta.fields:
    if df.fieldtype == "Link" and df.options == "Cost Center":
        print("PARENT:", df.fieldname, df.options)
imeta = frappe.get_meta("Material Request Item")
for df in imeta.fields:
    if df.fieldtype == "Link" and df.options == "Cost Center":
        print("ITEM:", df.fieldname, df.options)

print("\n=== Cost Center link fields on Purchase Order (known-working) ===")
pmeta = frappe.get_meta("Purchase Order")
for df in pmeta.fields:
    if df.fieldtype == "Link" and df.options == "Cost Center":
        print("PO PARENT:", df.fieldname)

print("\n=== has_permission test on a fresh MR ===")
mr = frappe.get_doc({
    "doctype": "Material Request", "company": "Adama Investment Group",
    "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
    "aig_cost_center": DAIRY_CC,
    "items": [{"item_code": "AIG-INV-FEED", "qty": 2, "warehouse": f"Dairy Farm Store - {ABBR}",
               "schedule_date": frappe.utils.today()}],
})
mr.insert()
frappe.db.commit()
print("created:", mr.name, "aig_cost_center:", mr.aig_cost_center)
for ptype in ["read", "write", "submit"]:
    ok = frappe.has_permission("Material Request", ptype=ptype, doc=mr, throw=False)
    print(f"has_permission {ptype} (Dairy CC):", ok)

mr.aig_cost_center = AGRO_CC
for ptype in ["read", "submit"]:
    ok = frappe.has_permission("Material Request", ptype=ptype, doc=mr, throw=False)
    print(f"has_permission {ptype} (Agro CC):", ok)

frappe.set_user("Administrator")
frappe.delete_doc("Material Request", mr.name, ignore_permissions=True, force=True)
frappe.db.commit()
print("\nDIAG2_DONE")
