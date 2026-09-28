# AIG config - step 40d: raw User Permission introspection for enduser.agro.
import frappe
import pprint

U = "enduser.agro@aig.local"

print("=== raw User Permission rows (all) for", U, "===")
rows = frappe.get_all("User Permission",
                      filters={"user": U},
                      fields=["name", "allow", "for_value", "applicable_for",
                              "apply_to_all_doctypes", "is_default"])
for r in rows:
    print(r)

print("\n=== count by allow ===")
for allow in ["Cost Center", "Warehouse", "Item Group"]:
    n = frappe.db.count("User Permission", {"user": U, "allow": allow})
    print(allow, n)

print("\n=== get_user_permissions raw repr ===")
frappe.set_user(U)
from frappe.permissions import get_user_permissions
up = get_user_permissions(U)
pprint.pprint({k: v for k, v in up.items()})

print("\n=== do the referenced Cost Centers actually exist? ===")
for r in rows:
    if r.allow == "Cost Center":
        exists = frappe.db.exists("Cost Center", r.for_value)
        print(repr(r.for_value), "exists:", bool(exists))

frappe.set_user("Administrator")
print("\nDIAG3_DONE")
