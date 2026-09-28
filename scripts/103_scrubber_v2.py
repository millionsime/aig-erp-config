# 103_scrubber_v2.py -- v2 of the row/header CC scrubbers. The actual toast
# trigger: ERPNext fills the Stock Entry / Purchase Order HEADER cost_center
# (and new rows) with the Company default "Head Office - AIG"; enterprise-
# scoped users can't use that CC, so the unsaved doc fails its permission
# re-check. v2 Client Scripts scrub BOTH header and rows: keep them aligned to
# the document's enterprise CC (aig_cost_center), or blank until the user
# chooses one (server-side "Movement Defaults" then self-heals on save).

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


JS = """(function () {
\tvar FLAG = "__aig_cc_scrubbed";
\tfunction target_cc(frm) {
\t\treturn frm.doc.aig_cost_center || null;
\t}
\tfunction apply(frm, v) {
\t\tif (frm.doc.cost_center !== v) {
\t\t\tfrappe.model.set_value(frm.doc.doctype, frm.doc.name, "cost_center", v);
\t\t}
\t}
\tfunction scrub(frm, force) {
\t\tvar target = target_cc(frm);
\t\t// header: on a NEW doc, ERPNext injected the Company default CC. Until
\t\t// the user picks the enterprise CC, clear it so permission checks pass.
\t\tif (frm.doc.__islocal || force) {
\t\t\tapply(frm, target || null);
\t\t}
\t\t(frm.doc.items || []).forEach(function (row) {
\t\t\tvar want = target || null;
\t\t\tif (row.cost_center && row.cost_center !== want) {
\t\t\t\tfrappe.model.set_value(row.doctype, row.name, "cost_center", want);
\t\t\t}
\t\t});
\t\tfrm.__aig_cc_scrubbed = true;
\t}
\tfrappe.ui.form.on("__PARENT__", {
\t\trefresh: function (frm) {
\t\t\tif (!frm[FLAG]) { scrub(frm, false); frm[FLAG] = true; }
\t\t},
\t\taig_cost_center: function (frm) { scrub(frm, true); },
\t\t__TYPEFIELD__: function (frm) { scrub(frm, true); }
\t});
\tfrappe.ui.form.on("__CHILD__", {
\t\titem_code: function (frm) { setTimeout(function () { scrub(frm, false); }, 900); },
\t\ts_warehouse: function (frm) { setTimeout(function () { scrub(frm, false); }, 900); },
\t\tt_warehouse: function (frm) { setTimeout(function () { scrub(frm, false); }, 900); }
\t});
})();
"""

DOCS = [
    ("Stock Entry", "Stock Entry Item", "stock_entry_type"),
    ("Material Request", "Material Request Item", "material_request_type"),
    ("Purchase Order", "Purchase Order Item", "company"),
]

log("STEP 1: rewrite the three Client Scripts (v2)")
for parent, child, type_field in DOCS:
    name = f"AIG - Row CC Scrub ({parent})"
    js = JS.replace("__PARENT__", parent).replace("__CHILD__", child).replace("__TYPEFIELD__", type_field)
    s = frappe.get_doc("Client Script", name)
    s.script = js
    s.enabled = 1
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log(f"  rewritten: {name}")

log("")
log("STEP 2: clear cache")
frappe.clear_cache()

log("")
log("STEP 3: verify the exact UI states (server-side equivalent)")
U = "storekeeper.agro@aig.local"

# The REAL failing UI state: header cost_center = Head Office (injected)
frappe.set_user(U)
doc = frappe.new_doc("Stock Entry")
doc.company = COMPANY
doc.stock_entry_type = "Material Receipt"
doc.purpose = "Material Receipt"
doc.to_warehouse = "Dairy Farm Store - AIG"
doc.cost_center = "Head Office - AIG"   # <- what ERPNext injects on the form
doc.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                     "t_warehouse": "Dairy Farm Store - AIG",
                     "cost_center": "Head Office - AIG"})
doc.name = "new-stock-entry-evkvhxjiqj"
try:
    frappe.has_permission(doc, "read", user=U, throw=True)
    log("  SE header=HO (before scrub): READ OK (unexpected)")
except Exception:
    log("  SE header=HO (before scrub): READ FAIL  <- this was your toast")

# After the scrubber clears the header (user hasn't chosen CC yet)
doc2 = frappe.new_doc("Stock Entry")
doc2.company = COMPANY
doc2.stock_entry_type = "Material Receipt"
doc2.purpose = "Material Receipt"
doc2.to_warehouse = "Dairy Farm Store - AIG"
doc2.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                      "t_warehouse": "Dairy Farm Store - AIG"})
doc2.name = "new-stock-entry-after000"
try:
    frappe.has_permission(doc2, "read", user=U, throw=True)
    log("  SE header cleared (after scrub): READ OK")
except Exception:
    log("  !! SE header cleared: STILL FAILING")

# After the user picks the enterprise CC
doc3 = frappe.new_doc("Stock Entry")
doc3.company = COMPANY
doc3.stock_entry_type = "Material Receipt"
doc3.purpose = "Material Receipt"
doc3.to_warehouse = "Dairy Farm Store - AIG"
doc3.aig_cost_center = "Dairy Farm - AIG"
doc3.cost_center = "Dairy Farm - AIG"
doc3.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                      "t_warehouse": "Dairy Farm Store - AIG",
                      "cost_center": "Dairy Farm - AIG"})
doc3.name = "new-stock-entry-chosen0"
try:
    frappe.has_permission(doc3, "read", user=U, throw=True)
    log("  SE with enterprise CC chosen: READ OK")
except Exception:
    log("  !! SE with enterprise CC: STILL FAILING")
frappe.set_user("Administrator")

log("")
log("STEP 4: confirm the save-time self-heal is in place")
script = frappe.db.get_value("Server Script", "AIG - SE Movement Defaults", "script")
log(f"  self-heal lines present: {'self-heal: fill header aig_cost_center from warehouse CC' in (script or '')}")

log("")
log("DONE -- hard-refresh (Ctrl+Shift+R), then retry: new Stock Entry as storekeeper.agro")
