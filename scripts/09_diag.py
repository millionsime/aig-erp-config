# AIG config - read-only state diagnostic. Determines which build steps
# actually took effect on the live instance. Safe: no writes.
print("=== SERVER SCRIPTS ===")
for s in frappe.get_all("Server Script", fields=["name", "script_type", "reference_doctype", "doctype_event", "disabled"]):
    print(s)

print("\n=== three-way match version (v2 mentions Purchase Receipt Item) ===")
tw = frappe.db.get_value("Server Script", "AIG - Payment Three-Way Match", "script") or ""
print("v2?" , "Purchase Receipt Item" in tw, "| length", len(tw))

print("\n=== guard scripts present? ===")
for g in ["AIG - PO Guard Raw Submit", "AIG - PE Guard Raw Submit"]:
    print(g, "->", bool(frappe.db.exists("Server Script", g)))

print("\n=== CUSTOM DOCPERM: orphan rows (parent not set) ===")
orph = frappe.get_all("Custom DocPerm", filters=[["parent", "is", "not set"]], pluck="name")
orph += frappe.get_all("Custom DocPerm", filters={"parent": ""}, pluck="name")
print("orphan count:", len(set(orph)))

print("\n=== AIG Custom DocPerm rows (parent-based) ===")
for p in frappe.get_all("Custom DocPerm", filters={"role": ["like", "AIG%"]},
                        fields=["parent", "role", "permlevel", "read", "write", "create", "submit", "cancel", "amend"],
                        order_by="parent, role, permlevel"):
    print(p)

print("\n=== WORKFLOW #1 states (live DB) ===")
wf = frappe.get_doc("Workflow", "AIG Procurement Approval")
for s in wf.states:
    print(f"  state={s.state!r} doc_status={s.doc_status} allow_edit={s.allow_edit}")
print("--- transitions ---")
for t in wf.transitions:
    print(f"  {t.state!r} --[{t.action}]--> {t.next_state!r}  allowed={t.allowed!r} cond={t.condition!r}")

print("\n=== WORKFLOW #2 states/transitions (live DB) ===")
wf2 = frappe.get_doc("Workflow", "AIG Payment Approval")
for s in wf2.states:
    print(f"  state={s.state!r} doc_status={s.doc_status} allow_edit={s.allow_edit}")
for t in wf2.transitions:
    print(f"  {t.state!r} --[{t.action}]--> {t.next_state!r} allowed={t.allowed!r}")

print("\n=== PO custom field aig_cost_center (reqd?) ===")
cf = frappe.db.get_value("Custom Field", {"dt": "Purchase Order", "fieldname": "aig_cost_center"},
                         ["reqd", "fieldtype", "options", "permlevel"], as_dict=True)
print(cf)
print("native cost_center on PO meta?", "cost_center" in [f.fieldname for f in frappe.get_meta("Purchase Order").fields])

print("\n=== PROPERTY SETTERS (Supplier banking / PO) ===")
for ps in frappe.get_all("Property Setter", filters={"doc_type": ["in", ["Supplier", "Purchase Order", "Payment Entry"]]},
                         fields=["name", "doc_type", "field_name", "property", "value"]):
    print(ps)

print("\n=== USER PERMISSIONS (Cost Center scoping) ===")
for up in frappe.get_all("User Permission", filters={"allow": "Cost Center"},
                         fields=["user", "for_value", "applicable_for"], order_by="user"):
    print(up)

print("\n=== BUDGETS ===")
for b in frappe.get_all("Budget", fields=["name", "cost_center", "account", "budget_amount", "action_if_annual_budget_exceeded_on_po"]):
    print(b)

print("\n=== WORKSPACES (AIG) ===")
print(frappe.get_all("Workspace", filters={"label": ["like", "AIG%"]}, fields=["name", "label", "module", "public"]))

print("\n=== EXISTING DEMO DOCS ===")
for dt in ["Purchase Order", "Purchase Receipt", "Purchase Invoice", "Payment Entry"]:
    print(dt, frappe.get_all(dt, fields=["name", "docstatus"], limit=20))

print("\nDIAG_DONE")
