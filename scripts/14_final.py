# AIG final consolidated state snapshot + tidy the stray Draft test artifact.
import frappe

C = "Adama Investment Group"

print("=== ROLES (AIG) ===")
print(frappe.get_all("Role", filters={"name": ["like", "AIG%"]}, pluck="name", order_by="name"))

print("\n=== USERS (AIG) count + roles ===")
for u in frappe.get_all("User", filters=[["email", "like", "%@aig.local"]], fields=["name", "full_name"], order_by="name"):
    roles = [r.role for r in frappe.get_doc("User", u.name).roles if r.role.startswith("AIG")]
    print(f"  {u.name:32s} {u.full_name:34s} {roles}")

print("\n=== USER PERMISSIONS (Cost Center scoping) ===")
for up in frappe.get_all("User Permission", filters={"allow": "Cost Center"}, fields=["user", "for_value"], order_by="user, for_value"):
    print(f"  {up.user:32s} -> {up.for_value}")

print("\n=== WORKFLOWS ===")
for w in frappe.get_all("Workflow", filters={"name": ["like", "AIG%"]}, fields=["name", "document_type", "is_active"]):
    print(" ", w)

print("\n=== SERVER SCRIPTS (AIG) ===")
for s in frappe.get_all("Server Script", filters={"name": ["like", "AIG%"]},
                        fields=["name", "reference_doctype", "doctype_event", "disabled"], order_by="name"):
    print(" ", s)

print("\n=== BUDGETS (docstatus must be 1 to enforce) ===")
for b in frappe.get_all("Budget", filters={"company": C},
                        fields=["name", "cost_center", "budget_amount", "docstatus", "action_if_annual_budget_exceeded_on_po"]):
    print(" ", b)

print("\n=== TAX CONFIG ===")
print("  Tax Withholding Category:", frappe.get_all("Tax Withholding Category", pluck="name"))
print("  Purchase Taxes Template :", frappe.get_all("Purchase Taxes and Charges Template", filters={"company": C}, pluck="name"))

print("\n=== WORKSPACES (AIG) ===")
print(" ", frappe.get_all("Workspace", filters={"label": ["like", "AIG%"]}, fields=["label", "module"]))

print("\n=== CUSTOM FIELDS (AIG) ===")
for cf in frappe.get_all("Custom Field", filters={"fieldname": ["like", "aig%"]}, fields=["dt", "fieldname", "fieldtype", "reqd", "permlevel"]):
    print(" ", cf)

# ---- tidy the stray Draft Payment Entry left by the negative Three-Way test ----
print("\n=== TIDY: negative Three-Way test artifact (reference_no AIGDEMO-T5A) ===")
for pe in frappe.get_all("Payment Entry", filters={"docstatus": 0, "reference_no": "AIGDEMO-T5A"}, pluck="name"):
    frappe.delete_doc("Payment Entry", pe, ignore_permissions=True, force=True)
    print("  DELETED draft PE", pe)
frappe.db.commit()

print("\n=== FINAL DEMO DOCS ===")
for dt in ["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry"]:
    for d in frappe.get_all(dt, fields=["name", "docstatus", "workflow_state"] if dt in ("Purchase Order", "Payment Entry") else ["name", "docstatus"], order_by="name"):
        print(f"  {dt:16s} {d}")

print("\nFINAL_DONE")
