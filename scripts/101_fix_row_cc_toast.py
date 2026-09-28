# 101_fix_row_cc_toast.py -- Fix the "Not permitted: read on Stock Entry
# new-..." toast. Cause: ERPNext auto-fills new item rows with the Company
# default cost center (Head Office - AIG); enterprise-scoped users (e.g. Agro)
# are not allowed to use that CC, so the unsaved doc fails the permission
# check. Fix: Client Scripts on Stock Entry / Material Request / Purchase
# Order that scrub row cost_center to the document's enterprise CC (or blank
# until chosen). Also backfill missing Warehouse.aig_cost_center values.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


JS_TEMPLATE = """(function () {
\tfunction target_cc(frm) {
\t\treturn frm.doc.aig_cost_center || frm.doc.cost_center || null;
\t}
\tfunction scrub(frm) {
\t\tconst target = target_cc(frm);
\t\t(frm.doc.items || []).forEach(function (row) {
\t\t\tif (!row.cost_center) return;
\t\t\tif (target && row.cost_center !== target) {
\t\t\t\tfrappe.model.set_value(row.doctype, row.name, "cost_center", target);
\t\t\t} else if (!target) {
\t\t\t\t// user has not chosen the enterprise CC yet: clear the injected
\t\t\t\t// company default so the doc stays within the user's scope
\t\t\t\tfrappe.model.set_value(row.doctype, row.name, "cost_center", null);
\t\t\t}
\t\t});
\t}
\tfrappe.ui.form.on("__PARENT__", {
\t\trefresh: scrub,
\t\taig_cost_center: scrub,
\t\t__TYPEFIELD__: scrub
\t});
\tfrappe.ui.form.on("__CHILD__", {
\t\tcost_center: function (frm) { scrub(frm); },
\t\titem_code: function (frm) { setTimeout(function () { scrub(frm); }, 900); },
\t\ts_warehouse: function (frm) { setTimeout(function () { scrub(frm); }, 900); },
\t\tt_warehouse: function (frm) { setTimeout(function () { scrub(frm); }, 900); }
\t});
})();
"""

DOCS = [
    ("Stock Entry", "Stock Entry Item", "stock_entry_type"),
    ("Material Request", "Material Request Item", "material_request_type"),
    ("Purchase Order", "Purchase Order Item", "transaction_date"),  # PO: scrub on refresh/CC set; type field not present
]
DOCS[2] = ("Purchase Order", "Purchase Order Item", "company")

log("STEP 1: install row-CC scrub Client Scripts")
for parent, child, type_field in DOCS:
    name = f"AIG - Row CC Scrub ({parent})"
    js = (
        JS_TEMPLATE.replace("__PARENT__", parent)
        .replace("__CHILD__", child)
        .replace("__TYPEFIELD__", type_field)
    )
    if frappe.db.exists("Client Script", name):
        s = frappe.get_doc("Client Script", name)
        s.script = js
        s.enabled = 1
        s.dt = parent
        s.view = "Form"
        s.flags.ignore_permissions = True
        s.save(ignore_permissions=True)
        log(f"  updated: {name}")
    else:
        frappe.get_doc({
            "doctype": "Client Script",
            "name": name,          # autoname = Prompt -> explicit name needed
            "dt": parent,
            "view": "Form",
            "enabled": 1,
            "script": js,
        }).insert(ignore_permissions=True)
        log(f"  created: {name}")

log("")
log("STEP 2: backfill Warehouse.aig_cost_center (10 missing)")
WH_CC = {
    "Andode Store - AIG": "Construction Enterprise - AIG",
    "Open Store - AIG": "Head Office - AIG",
    "Qera Abota Store - AIG": "Head Office - AIG",
    "Process Store - AIG": "Head Office - AIG",
    "Stores - AIG": "Head Office - AIG",
    "AIG Stores - AIG": "Head Office - AIG",
    "Goods In Transit - AIG": "Head Office - AIG",
    "Finished Goods - AIG": "Head Office - AIG",
    "Work In Progress - AIG": "Head Office - AIG",
    "All Warehouses - AIG": "Head Office - AIG",
}
for wh, cc in WH_CC.items():
    cur = frappe.db.get_value("Warehouse", wh, "aig_cost_center")
    if cur:
        log(f"  {wh}: already {cur}")
        continue
    frappe.db.set_value("Warehouse", wh, "aig_cost_center", cc)
    log(f"  {wh}: -> {cc}")

log("")
log("STEP 3: clear caches")
frappe.clear_cache()

log("")
log("STEP 4: re-run the failing probes (server-side equivalent)")
from frappe.permissions import has_permission as hp  # noqa

U = "storekeeper.agro@aig.local"
frappe.set_user(U)
doc = frappe.new_doc("Stock Entry")
doc.company = COMPANY
doc.stock_entry_type = "Material Receipt"
doc.purpose = "Material Receipt"
doc.to_warehouse = "Dairy Farm Store - AIG"
doc.aig_cost_center = "Dairy Farm - AIG"
doc.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                     "t_warehouse": "Dairy Farm Store - AIG",
                     "cost_center": "Dairy Farm - AIG"})
doc.name = "new-stock-entry-evkvhxjiqj"
try:
    hp(doc, "read", user=U, throw=True)
    log("  SE with enterprise row CC: READ OK")
except Exception:
    log("  !! SE with enterprise row CC: STILL FAILING")

# empty row CC (what the scrubber produces when no CC chosen yet)
doc2 = frappe.new_doc("Stock Entry")
doc2.company = COMPANY
doc2.stock_entry_type = "Material Receipt"
doc2.purpose = "Material Receipt"
doc2.to_warehouse = "Dairy Farm Store - AIG"
doc2.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                      "t_warehouse": "Dairy Farm Store - AIG"})
doc2.name = "new-stock-entry-fresh00000"
try:
    hp(doc2, "read", user=U, throw=True)
    log("  SE with empty row CC: READ OK")
except Exception:
    log("  !! SE with empty row CC: STILL FAILING")
frappe.set_user("Administrator")

log("")
log("STEP 5: client script inventory (enabled)")
for cs in frappe.get_all("Client Script", filters={"dt": ("in", ["Stock Entry", "Material Request", "Purchase Order"])},
                         fields=["name", "enabled"]):
    log(f"  {cs.name}: {'enabled' if cs.enabled else 'DISABLED'}")

log("")
log("DONE -- hard-refresh the browser (Ctrl+Shift+R) and retry the form.")
