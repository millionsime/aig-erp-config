# AIG config - step 31: INVENTORY MASTERS (config layer only, additive/idempotent).
# Creates: warehouse store tree, warehouse types, item groups for the four AIG
# classifications, Custom Fields on Item + Warehouse, and a NON-BLOCKING
# duplicate-item-name guard Server Script.
# NO core frappe/erpnext file is edited. Run via run_script.sh.
import frappe
import traceback

COMPANY = "Adama Investment Group"
ABBR = "AIG"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def insert_doc(values, label):
    doc = frappe.get_doc(values)
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"{label}: {doc.name}")
        return doc.name
    except Exception:
        print(f"!! FAILED {label}")
        print(traceback.format_exc())
        return None


def get_or_create(dt, filters, values, label):
    name = frappe.db.get_value(dt, filters)
    if name:
        log("EXISTS", f"{label}: {name}")
        return name
    merged = {"doctype": dt}
    merged.update(values)
    return insert_doc(merged, label)


def cf(dt, fieldname, values, label):
    """Idempotent Custom Field creation."""
    if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
        log("EXISTS", f"Custom Field {dt}.{fieldname}")
        return fieldname
    merged = {"doctype": "Custom Field", "dt": dt, "fieldname": fieldname}
    merged.update(values)
    return insert_doc(merged, label)


# ============================================================== warehouse types
for wt in ["Main Store", "Enterprise Store", "Project Store", "Process/Other Store"]:
    get_or_create("Warehouse Type", {"name": wt}, {"doctype": "Warehouse Type", "name": wt},
                  f"Warehouse Type {wt}")

# ============================================================ warehouse tree
# One organising group under the company root; the 13 diagram stores live in it.
# Existing Stores/WIP/Finished Goods/Goods In Transit are left untouched.
ROOT_WH = f"All Warehouses - {ABBR}"
GROUP_WH = get_or_create("Warehouse", {"warehouse_name": "AIG Stores", "company": COMPANY}, {
    "doctype": "Warehouse", "warehouse_name": "AIG Stores", "company": COMPANY,
    "is_group": 1, "parent_warehouse": ROOT_WH,
}, "Warehouse group AIG Stores")

# (warehouse_name, mapped cost center or None, warehouse type, is_main)
# Ambiguous stores (None) are created but left UNMAPPED and FLAGGED - we do not
# guess an enterprise (brief: "Do not create or guess an additional enterprise").
STORES = [
    ("Main Store",       f"Head Office - {ABBR}",          "Main Store",           1),
    ("Dairy Farm Store", f"Dairy Farm - {ABBR}",           "Enterprise Store",     0),
    ("Poultry Farm Store", f"Poultry Farm - {ABBR}",       "Enterprise Store",     0),
    ("Animal Feed Plant", f"Animal Feed Factory - {ABBR}", "Enterprise Store",     0),
    ("Process Store",    None,                              "Process/Other Store",  0),
    ("Qera Abota Store", None,                              "Process/Other Store",  0),
    ("Project Store",    f"Construction - {ABBR}",         "Project Store",        0),
    ("Open Store",       None,                              "Process/Other Store",  0),
    ("Andode Store",     None,                              "Process/Other Store",  0),
    ("Garage Store",     f"Guaraj (Garage) - {ABBR}",      "Enterprise Store",     0),
    ("Fuel Store",       f"Fuel Station - {ABBR}",         "Enterprise Store",     0),
    ("Parks Store",      f"Cafeteria and Parks - {ABBR}",  "Enterprise Store",     0),
    # Source spelling "Cafe Store" (diagram "Café Store"); ASCII used to avoid
    # any encoding risk in the runner pipeline. Flagged in the guide.
    ("Cafe Store",       f"Cafeteria and Parks - {ABBR}",  "Enterprise Store",     0),
]

WH = {}
for wname, cc, wtype, is_main in STORES:
    full = f"{wname} - {ABBR}"
    vals = {
        "doctype": "Warehouse", "warehouse_name": wname, "company": COMPANY,
        "is_group": 0, "parent_warehouse": GROUP_WH or ROOT_WH,
        "warehouse_type": wtype,
    }
    created = get_or_create("Warehouse", {"warehouse_name": wname, "company": COMPANY}, vals,
                            f"Warehouse {wname}")
    WH[wname] = created or full
    # enterprise mapping via custom field (set separately so re-runs update it)
    if cc and frappe.db.exists("Cost Center", cc):
        try:
            frappe.db.set_value("Warehouse", WH[wname], "aig_cost_center", cc, update_modified=False)
            frappe.db.set_value("Warehouse", WH[wname], "aig_is_main_store", is_main, update_modified=False)
        except Exception:
            # custom field may not exist yet on first pass; set after cf() below
            pass
    elif not cc:
        log("FLAG", f"Warehouse {wname}: enterprise/cost-center mapping UNRESOLVED (needs AIG input)")

# ========================================================== item groups
# Four AIG classifications under a dedicated parent group. Keep the default
# ERPNext groups intact; this is additive.
IG_PARENT = get_or_create("Item Group", {"item_group_name": "AIG Inventory"}, {
    "doctype": "Item Group", "item_group_name": "AIG Inventory",
    "parent_item_group": "All Item Groups", "is_group": 1,
}, "Item Group AIG Inventory (parent)")

for ig_name, ig_type in [
    ("Consumable Stock", "stock"),
    ("Property & Fixed Assets", "asset"),
    ("Livestock & Biological Assets", "biological"),
    ("Forms & Vouchers", "nonstock"),
]:
    get_or_create("Item Group", {"item_group_name": ig_name}, {
        "doctype": "Item Group", "item_group_name": ig_name,
        "parent_item_group": IG_PARENT or "All Item Groups", "is_group": 0,
    }, f"Item Group {ig_name}")

# ======================================================= Custom Fields: Item
cf("Item", "aig_item_classification", {
    "label": "AIG Classification", "fieldtype": "Select",
    "options": "\nConsumable Stock\nProperty/Fixed Asset\nLivestock/Biological\nForms/Vouchers\nOther",
    "insert_after": "item_group", "in_list_view": 1, "in_standard_filter": 1,
}, "Custom Field Item.aig_item_classification")

cf("Item", "aig_local_name", {
    "label": "Local / Alternate Name", "fieldtype": "Data",
    "insert_after": "item_name", "description": "Preserve source or local-language name from records.",
}, "Custom Field Item.aig_local_name")

cf("Item", "aig_bin_location", {
    "label": "Bin / Location", "fieldtype": "Data",
    "insert_after": "aig_local_name",
    "description": "Assigned by Property Administration Expert.",
}, "Custom Field Item.aig_bin_location")

cf("Item", "aig_property_tag", {
    "label": "Property / Asset Tag", "fieldtype": "Data",
    "insert_after": "aig_bin_location",
}, "Custom Field Item.aig_property_tag")

cf("Item", "aig_default_enterprise_cc", {
    "label": "Default Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "aig_property_tag",
}, "Custom Field Item.aig_default_enterprise_cc")

# ================================================ Custom Fields: Warehouse
cf("Warehouse", "aig_cost_center", {
    "label": "AIG Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "warehouse_name", "in_list_view": 1, "in_standard_filter": 1,
    "description": "Owning enterprise for this store. Used to scope access and reports.",
}, "Custom Field Warehouse.aig_cost_center")

cf("Warehouse", "aig_is_main_store", {
    "label": "Is Main Store", "fieldtype": "Check",
    "insert_after": "aig_cost_center",
    "description": "Main Store triggers the extra final-approval step on receiving.",
}, "Custom Field Warehouse.aig_is_main_store")

cf("Warehouse", "aig_store_manager_role", {
    "label": "Store Administrator Role", "fieldtype": "Link", "options": "Role",
    "insert_after": "aig_is_main_store",
}, "Custom Field Warehouse.aig_store_manager_role")

# Now that Warehouse.aig_cost_center exists, (re)apply the confident mappings.
frappe.db.commit()
for wname, cc, wtype, is_main in STORES:
    target = WH.get(wname)
    if not target or not frappe.db.exists("Warehouse", target):
        continue
    if cc and frappe.db.exists("Cost Center", cc):
        frappe.db.set_value("Warehouse", target, "aig_cost_center", cc, update_modified=False)
    frappe.db.set_value("Warehouse", target, "aig_is_main_store", is_main, update_modified=False)
frappe.db.commit()

# ================================ Server Script: duplicate item NAME warning
# Non-blocking (msgprint) reviewable warning - never merges or edits items.
DUP_NAME = """# AIG - Item Duplicate Name Warning (Before Insert)
# Presents a reviewable warning when another Item already uses the same item_name.
# Does NOT block and does NOT merge: item_code stays the unique key.
existing = frappe.db.get_all(
    "Item",
    filters={"item_name": doc.item_name, "name": ["!=", doc.name]},
    fields=["name", "item_code"],
    limit=10,
)
if existing:
    found = ", ".join([str(e.name) for e in existing])
    frappe.msgprint(
        "AIG duplicate-name check: item name '" + str(doc.item_name) +
        "' already exists on: " + found +
        ". Review before saving. Items are NOT merged automatically.",
        title="Possible Duplicate Item Name",
        indicator="orange",
    )
"""

if frappe.db.exists("Server Script", "AIG - Item Duplicate Name Warning"):
    ss = frappe.get_doc("Server Script", "AIG - Item Duplicate Name Warning")
    if ss.script != DUP_NAME or ss.disabled:
        ss.script = DUP_NAME
        ss.disabled = 0
        ss.flags.ignore_permissions = True
        ss.save(ignore_permissions=True)
        log("UPDATE", "Server Script AIG - Item Duplicate Name Warning")
    else:
        log("EXISTS", "Server Script AIG - Item Duplicate Name Warning")
else:
    insert_doc({
        "doctype": "Server Script", "name": "AIG - Item Duplicate Name Warning",
        "script_type": "DocType Event", "reference_doctype": "Item",
        "doctype_event": "Before Insert", "script": DUP_NAME, "disabled": 0,
    }, "Server Script AIG - Item Duplicate Name Warning")

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP31_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
