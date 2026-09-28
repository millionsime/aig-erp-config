# AIG config - step 42b: list cost centers to pick a valid non-Agro isolation target.
import frappe

ABBR = "AIG"
print("=== all Cost Centers (non-group first) ===")
rows = frappe.get_all("Cost Center",
                      fields=["name", "cost_center_name", "is_group", "parent_cost_center"],
                      order_by="is_group asc, name asc")
for r in rows:
    print(f"  {r.name!r}  group={r.is_group}  parent={r.parent_cost_center!r}")

print("\n=== enduser.agro allowed cost centers ===")
print(frappe.get_all("User Permission",
      filters={"user": "enduser.agro@aig.local", "allow": "Cost Center"}, pluck="for_value"))
print("\nLIST_DONE")
