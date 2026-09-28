# AIG config - step 30: READ-ONLY inventory inspection.
# Prints everything the inventory build needs to know before creating anything.
# No writes. Run via run_script.sh.
import frappe

COMPANY = "Adama Investment Group"


def hdr(t):
    print("\n=== " + t + " ===")


hdr("SITE BASICS")
print("installed apps:", frappe.get_installed_apps())
try:
    import erpnext
    print("erpnext version:", getattr(erpnext, "__version__", "unknown"))
except Exception as e:
    print("erpnext version err:", e)
print("server_script_enabled:", frappe.conf.get("server_script_enabled"))

hdr("COMPANIES")
for c in frappe.get_all("Company", fields=["name", "default_currency", "abbr", "enable_perpetual_inventory", "stock_received_but_not_billed"]):
    print(c)

hdr("WAREHOUSES")
for w in frappe.get_all("Warehouse", fields=["name", "warehouse_name", "is_group", "company", "parent_warehouse", "warehouse_type"], order_by="lft"):
    print(f"{'[G]' if w.is_group else '   '} {w.name}  parent={w.parent_warehouse} type={w.warehouse_type}")

hdr("WAREHOUSE TYPES")
print(frappe.get_all("Warehouse Type", pluck="name"))

hdr("COST CENTERS (active)")
for cc in frappe.get_all("Cost Center", filters={"disabled": 0}, fields=["name", "cost_center_name", "parent_cost_center", "company", "is_group"], order_by="lft"):
    print(f"{'[G]' if cc.is_group else '   '} {cc.name}  parent={cc.parent_cost_center}")

hdr("ACCOUNTING DIMENSIONS")
try:
    for ad in frappe.get_all("Accounting Dimension", fields=["name", "label", "document_type", "disabled"]):
        print(ad)
except Exception as e:
    print("acct dim err:", e)

hdr("ITEM GROUPS")
for ig in frappe.get_all("Item Group", fields=["name", "parent_item_group", "is_group"], order_by="lft"):
    print(f"{'[G]' if ig.is_group else '   '} {ig.name} parent={ig.parent_item_group}")

hdr("ITEMS (count + sample)")
print("item count:", frappe.db.count("Item"))
for it in frappe.get_all("Item", fields=["item_code", "item_name", "item_group", "is_stock_item", "is_fixed_asset", "stock_uom", "has_batch_no", "has_serial_no"], limit=15):
    print(it)

hdr("UOMS")
print(frappe.get_all("UOM", pluck="name"))

hdr("ROLES (AIG + stock-ish)")
print("AIG roles:", frappe.get_all("Role", filters={"name": ["like", "AIG%"]}, pluck="name"))
for rn in ["Stock Manager", "Stock User", "Item Manager", "Purchase User", "System Manager"]:
    print(rn, "exists:", bool(frappe.db.exists("Role", rn)))

hdr("USERS (@aig.local)")
for u in frappe.get_all("User", filters=[["email", "like", "%@aig.local"]], fields=["name", "full_name", "enabled"]):
    print(u)

hdr("EXISTING WORKFLOWS")
for w in frappe.get_all("Workflow", fields=["name", "document_type", "is_active"]):
    print(w)

hdr("WORKFLOW STATES")
print(frappe.get_all("Workflow State", pluck="name"))

hdr("WORKFLOW ACTION MASTERS")
print(frappe.get_all("Workflow Action Master", pluck="name"))

hdr("SERVER SCRIPTS (existing)")
for s in frappe.get_all("Server Script", fields=["name", "script_type", "reference_doctype", "doctype_event", "disabled"]):
    print(s)

hdr("CUSTOM FIELDS on stock doctypes")
for dt in ["Stock Entry", "Material Request", "Purchase Receipt", "Item", "Warehouse", "Stock Reconciliation", "Delivery Note", "Material Transfer"]:
    cfs = frappe.get_all("Custom Field", filters={"dt": dt}, fields=["fieldname", "label", "fieldtype"])
    if cfs:
        print(dt, "->", cfs)
    else:
        print(dt, "-> (none)")

hdr("PRINT FORMATS (AIG / Model / Quality)")
for pf in frappe.get_all("Print Format", fields=["name", "doc_type", "standard", "module"]):
    n = (pf.name or "").lower()
    if any(k in n for k in ["aig", "model", "quality", "issue", "receipt"]):
        print(pf)

hdr("EXISTING CUSTOM DOCTYPES (non-core apps)")
try:
    for d in frappe.get_all("DocType", filters={"custom": 1}, fields=["name", "module", "issingle"]):
        print(d)
except Exception as e:
    print("err:", e)

hdr("STOCK SETTINGS / GLOBAL DEFAULTS")
try:
    ss = frappe.get_cached_doc("Stock Settings")
    print("allow_negative_stock:", ss.allow_negative_stock)
    print("default_warehouse:", getattr(ss, "default_warehouse", None))
except Exception as e:
    print("stock settings err:", e)

hdr("STOCK ENTRY TYPES (purpose values in use)")
print(frappe.db.sql("select distinct purpose from `tabStock Entry` limit 20"))

hdr("DOCUMENT NAMING SERIES (stock)")
try:
    ns = frappe.get_cached_doc("Naming Series")
except Exception:
    ns = None
for dt in ["Stock Entry", "Material Request", "Purchase Receipt", "Stock Reconciliation"]:
    try:
        meta = frappe.get_meta(dt)
        f = meta.get_field("naming_series")
        print(dt, "naming options:", (f.options if f else None))
    except Exception as e:
        print(dt, "naming err:", e)

hdr("EXISTING AIG WORKSPACES")
for w in frappe.get_all("Workspace", fields=["name", "label", "module", "public"]):
    if "aig" in (w.label or "").lower():
        print(w)

print("\nINSPECT_DONE")
