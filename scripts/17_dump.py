import frappe
from frappe.model.workflow import get_transitions

C = "Adama Investment Group"

print("=== USERS + ROLES + ENABLED ===")
for u in frappe.get_all("User", filters=[["email", "like", "%@aig.local"]],
                        fields=["name", "full_name", "enabled"], order_by="name"):
    d = frappe.get_doc("User", u.name)
    roles = sorted([r.role for r in d.roles if r.role.startswith("AIG")])
    print(f"  {u.name:34s} | {u.full_name:30s} | enabled={u.enabled} | {roles}")

print("\n=== WORKFLOWS: states + transitions ===")
for wname in frappe.get_all("Workflow", filters={"name": ["like", "AIG%"]}, pluck="name"):
    w = frappe.get_doc("Workflow", wname)
    print(f"\n--- {w.workflow_name}  (DocType: {w.document_type}, active={w.is_active}) ---")
    print("  STATES:")
    for s in w.states:
        print(f"    state={s.state:36s} docstatus={s.doc_status} allow_edit={s.allow_edit}")
    print("  TRANSITIONS:")
    for t in w.transitions:
        cond = f"  IF [{t.condition}]" if t.condition else ""
        print(f"    {t.state:34s} --{t.action:28s}--> {t.next_state:34s} (allowed: {t.allowed}){cond}")

print("\n=== EXISTING DEMO DOCS ===")
for dt in ["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry"]:
    flds = ["name", "docstatus"]
    if dt in ("Purchase Order", "Payment Entry"):
        flds.append("workflow_state")
    for d in frappe.get_all(dt, fields=flds, order_by="name"):
        print(f"  {dt:16s} {d}")

print("\n=== ITEMS (AIG) ===")
for it in frappe.get_all("Item", filters={"name": ["like", "AIG%"]},
                         fields=["name", "item_name", "is_stock_item", "stock_uom"], order_by="name"):
    print(" ", it)

print("\n=== SUPPLIERS ===")
for s in frappe.get_all("Supplier", filters={"supplier_group": "AIG Vendors"},
                        fields=["name", "supplier_name"], order_by="name"):
    print(" ", s)

print("\n=== COST CENTERS (leaf-ish list) ===")
for cc in frappe.get_all("Cost Center", filters={"company": C},
                         fields=["name", "is_group", "parent_cost_center"], order_by="name"):
    print(" ", cc)

print("\n=== WAREHOUSES ===")
print(frappe.get_all("Warehouse", filters={"company": C}, pluck="name"))

print("\nDUMP_DONE")
