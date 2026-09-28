# 92_inventory_verify.py -- Read-only verification that the inventory layer
# (workflows, roles, users, print formats, workspaces, server scripts,
# warehouses, items) survived the transaction purge. Also checks whether
# items still have expense-account defaults (needed for Material Issue).

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("1) INVENTORY WORKFLOWS")
for w in frappe.get_all("Workflow", fields=["name", "document_type", "is_active"]):
    states = frappe.get_all(
        "Workflow Document State", filters={"parent": w.name}, fields=["state", "doc_status", "allow_edit"],
        order_by="idx",
    )
    trans = frappe.get_all(
        "Workflow Transition", filters={"parent": w.name},
        fields=["state", "action", "next_state", "allowed"], order_by="idx",
    )
    log(f"  {w.name} ({w.document_type}) active={w.is_active}")
    for s in states:
        log(f"    state: {s.state} (doc_status={s.doc_status}, edit={s.allow_edit})")
    for t in trans:
        log(f"    trans: [{t.allowed}] {t.state} --{t.action}--> {t.next_state}")

log("")
log("2) INVENTORY ROLES")
for r in ["AIG Inventory Administrator", "AIG Main Store Administrator", "AIG General Store Keeper",
          "AIG Store Keeper", "AIG Property Admin Expert", "AIG End User", "AIG Internal Auditor"]:
    log(f"  {r}: {'OK' if frappe.db.exists('Role', r) else 'MISSING'}")

log("")
log("3) DEMO USERS + ROLES + SCOPES")
for u in frappe.get_all("User", filters={"email": ("like", "%aig.local")}, fields=["name", "enabled"], order_by="name"):
    roles = frappe.get_all("Has Role", filters={"parent": u.name, "parenttype": "User"}, pluck="role")
    whs = frappe.get_all("User Permission", filters={"user": u.name, "allow": "Warehouse"}, pluck="for_value")
    ccs = frappe.get_all("User Permission", filters={"user": u.name, "allow": "Cost Center"}, pluck="for_value")
    log(f"  {u.name} enabled={u.enabled}")
    log(f"    roles: {roles}")
    if whs:
        log(f"    warehouses: {whs}")
    if ccs:
        log(f"    cost centers: {len(ccs)}")

log("")
log("4) PRINT FORMATS (Model 19/22, Quality, issue docs)")
for p in frappe.get_all("Print Format", fields=["name", "doc_type", "disabled"], order_by="name"):
    log(f"  {p.name} ({p.doc_type}){' [disabled]' if p.disabled else ''}")

log("")
log("5) WORKSPACES (inventory-related)")
for w in frappe.get_all("Workspace", fields=["name", "module", "public"], order_by="name"):
    log(f"  {w.name} (module={w.module}, public={w.public})")

log("")
log("6) INVENTORY SERVER SCRIPTS")
for s in frappe.get_all("Server Script", fields=["name", "disabled", "doctype_event"], order_by="name"):
    log(f"  {s.name} [{s.doctype_event}] {'DISABLED' if s.disabled else 'enabled'}")

log("")
log("7) STOCK STATE (after today's purge)")
log(f"  Items: {frappe.db.count('Item')} | Item Groups: {frappe.db.count('Item Group')} | Warehouses: {frappe.db.count('Warehouse', {'company': COMPANY})}")
log(f"  Stock Ledger Entries: {frappe.db.count('Stock Ledger Entry', {'company': COMPANY})} | Bins: {frappe.db.count('Bin')}")
log(f"  Material Requests: {frappe.db.count('Material Request', {'company': COMPANY})} | Stock Entries: {frappe.db.count('Stock Entry', {'company': COMPANY})}")

log("")
log("8) ITEMS + DEFAULTS (expense account needed for Material Issue)")
for it in frappe.get_all("Item", fields=["name", "item_name", "item_group", "is_stock_item", "stock_uom", "disabled"]):
    defaults = frappe.get_all(
        "Item Default", filters={"parent": it.name, "company": COMPANY},
        fields=["expense_account", "income_account", "default_warehouse"],
    )
    d = defaults[0] if defaults else None
    log(f"  {it.name} ({it.item_name}) group={it.item_group} stock={it.is_stock_item} disabled={it.disabled}")
    if d:
        log(f"    defaults: expense={d.expense_account} income={d.income_account} wh={d.default_warehouse}")
    else:
        log("    defaults: NONE")

comp_fields = sorted(
    r[0]
    for r in frappe.db.sql(
        "select fieldname from `tabDocField` where parent='Company' and fieldname like '%expense%'"
    )
)
vals = frappe.db.get_value("Company", COMPANY, comp_fields, as_dict=1)
log(f"  company expense defaults: { {k: v for k, v in vals.items() if v} }")

log("")
log("9) UOMs + Barcode field on Item")
log(f"  has barcode field: {'barcode' in {f.fieldname for f in frappe.get_meta('Item').fields}}")
