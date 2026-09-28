# 157b_normalize_hardening.py -- P0 bomb #2 (commits on success).
# "AIG - MR CC Normalize" silently passed a root/HO/empty header through when
# NO row warehouse carried an aig_cost_center -> the approval buttons vanish
# with no error (the demo's "no action button" scare, one wrong warehouse
# away). The patch keeps all existing behavior (derive header from the first
# row warehouse that has a CC, overwrite root/HO, sync rows) and adds a
# LOUD failure: if the header must be derived but no warehouse provides a
# CC, throw naming the offending warehouses. Sandbox-safe: no getattr, no
# flt, no str.format.
import frappe


def log(*a):
    print(*a, flush=True)


NORMALIZE = '''# AIG - MR CC Normalize (Before Validate): the workflow read check on the
# saved doc fails if the header carries a CC outside the requester's scope
# (root CC / Head Office). Derive the enterprise CC from the row warehouse,
# overwrite any root/HO value, and sync row cost centers. Runs before the
# workflow state is committed, so apply_workflow's doc-read always sees a
# document within the owner's enterprise scope. HARDENED (157b): if the
# header must be derived but NO row warehouse carries an aig_cost_center,
# throw naming the warehouses - a silent pass-through here used to leave the
# request with root/HO costing, which strips every workflow action button
# with no error. No getattr / flt / str.format (sandbox).
row_cc = None
missing = ""
for it in (doc.items or []):
    if it.warehouse:
        row_cc = frappe.db.get_value("Warehouse", it.warehouse, "aig_cost_center")
        if row_cc:
            break
        if missing:
            missing = missing + ", " + it.warehouse
        else:
            missing = it.warehouse
    else:
        if missing:
            missing = missing + ", (no warehouse)"
        else:
            missing = "(no warehouse)"
hdr = doc.get("aig_cost_center")
if hdr in ("Adama Investment Group - AIG", "Head Office - AIG", None, ""):
    if not row_cc:
        frappe.throw("AIG Cost Center: no cost center could be derived for "
                     "this request - warehouse(s) " + missing +
                     " have no AIG Cost Center configured (set it on the "
                     "Warehouse record) and the request header carries the "
                     "root/Head-Office cost center. Left unfixed, this "
                     "request would show no approval buttons at all.")
    hdr = row_cc
if hdr:
    doc.aig_cost_center = hdr
    for it in (doc.items or []):
        if it.cost_center in ("Adama Investment Group - AIG",
                              "Head Office - AIG", None, ""):
            it.cost_center = hdr
'''

row = frappe.get_doc("Server Script", "AIG - MR CC Normalize")
row.script = NORMALIZE
row.disabled = 0
row.flags.ignore_permissions = True
row.save(ignore_permissions=True)
log("AIG - MR CC Normalize hardened: missing warehouse CC now throws loudly")
frappe.clear_cache()

log("")
log("verify 1: ROOT header + warehouse WITHOUT aig_cost_center -> loud throw")
log("  (Request Defaults pre-empts empty headers via user-permission fallback; "
    "the guard is the safety net for the root/empty-header path)")
COMPANY = "Adama Investment Group"
ITEM = "AIG-ACCEPT-ITEM"
CC = "Animal Feed Factory - AIG"
BADWH = "Probe No-CC Store - AIG"
if not frappe.db.exists("Item", ITEM):
    frappe.get_doc({"doctype": "Item", "item_code": ITEM,
                    "item_name": "Accept Item",
                    "item_group": frappe.db.get_value(
                        "Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos", "is_stock_item": 1,
                    "is_purchase_item": 1}).insert(ignore_permissions=True)
if frappe.db.exists("Warehouse", BADWH):
    frappe.delete_doc("Warehouse", BADWH, force=True,
                      ignore_permissions=True)
wh = frappe.get_doc({"doctype": "Warehouse", "warehouse_name": BADWH,
                     "company": COMPANY, "is_group": 0,
                     "warehouse_type": "Transit"}).insert(
    ignore_permissions=True)
thrown = ""
try:
    frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(),
        "aig_cost_center": "Adama Investment Group - AIG",
        "aig_estimated_total": 5000,
        "items": [{"item_code": ITEM, "qty": 1, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 5000,
                   "warehouse": wh.name,
                   "cost_center": "Adama Investment Group - AIG"}],
    }).insert(ignore_permissions=True)
except Exception as e:
    thrown = str(e)
if "no cost center could be derived" in thrown and "Probe No-CC Store" in thrown:
    log(f"  PASS loud throw naming the warehouse: "
        f"{thrown.strip().splitlines()[0][:90]}...")
else:
    log(f"  FAIL expected loud throw, got: {thrown!r}")
    raise SystemExit("normalize hardening verification FAILED")

log("")
log("verify 2: good warehouse still normalizes (behavior unchanged)")
d = frappe.get_doc({
    "doctype": "Material Request", "company": COMPANY,
    "material_request_type": "Purchase",
    "transaction_date": frappe.utils.nowdate(),
    "aig_estimated_total": 5000,
    "items": [{"item_code": ITEM, "qty": 1, "uom": "Nos",
               "schedule_date": frappe.utils.nowdate(), "rate": 5000,
               "warehouse": "Animal Feed Plant - AIG"}],
})
d.insert(ignore_permissions=True)
name2 = d.name
got = frappe.db.get_value("Material Request", name2, "aig_cost_center")
log(f"  header aig_cost_center = {got!r}")
frappe.delete_doc("Material Request", name2, force=True,
                  ignore_permissions=True)
if got != CC:
    raise SystemExit("normalize positive path FAILED")
frappe.delete_doc("Warehouse", BADWH, force=True, ignore_permissions=True)
log("  (probe MR deleted, probe warehouse deleted)")
log("no residue - commit persists only the script + log")
log("DONE 157b")
