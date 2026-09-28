# 110_mr_stock_item_guard.py -- Prevent the "not a stock Item" dead end:
# a Material Issue (Model 19 stock request) must only contain STOCK items.
# ERPNext allowed the request (MRs legitimately carry non-stock items for
# purchasing), which only exploded later when the Store Keeper tried to post
# the issue. Add a Before-Validate guard with a clear message at request time.

import frappe

COMPANY = "Adama Investment Group"
U = "enduser.agro@aig.local"


def log(*a):
    print(*a, flush=True)


GUARD = '''# AIG - a stock request (Material Issue / Model 19) may only contain STOCK
# items; non-stock items belong to Purchase-type requests (Procurement).
if doc.material_request_type == "Material Issue":
    bad = []
    for it in (doc.items or []):
        if not it.item_code:
            continue
        is_stock = frappe.db.get_value("Item", it.item_code, "is_stock_item")
        if not is_stock:
            bad.append(it.item_code)
    if bad:
        frappe.throw(
            "AIG stock request: these items are NOT stock items and cannot be "
            "issued from a store: " + str(bad) + ". Use a stock item (for demo: "
            "AIG-INV-FEED 'AIG Demo Dairy Feed' -- 500 bags in Dairy Farm Store), "
            "or raise a Purchase-type request via a Procurement Officer."
        )'''

log("STEP 1: Server Script 'AIG - MR Stock Item Guard' (Before Validate)")
if frappe.db.exists("Server Script", "AIG - MR Stock Item Guard"):
    s = frappe.get_doc("Server Script", "AIG - MR Stock Item Guard")
    s.script = GUARD
    s.enabled = 1
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Server Script",
        "name": "AIG - MR Stock Item Guard",
        "script_type": "DocType Event",
        "doctype_event": "Before Validate",
        "reference_doctype": "Material Request",
        "enabled": 1,
        "script": GUARD,
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("STEP 2: clear cache")
frappe.clear_cache()

log("")
log("STEP 3: VERIFY -- non-stock item request must be blocked AT REQUEST TIME")
frappe.set_user(U)
blocked = False
msg = ""
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue",
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "items": [{"item_code": "AIG-DAIRY-FEED", "qty": 5,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert()
except Exception:
    blocked = True
    tb = frappe.get_traceback().strip().splitlines()
    msg = next((ln for ln in reversed(tb) if "NOT stock items" in ln), tb[-1])
log(f"  non-stock request blocked: {blocked}")
log(f"  message: {msg[:170]}")

log("")
log("STEP 4: VERIFY -- stock item request still goes through")
probe = None
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue",
        "schedule_date": frappe.utils.today(),
        "aig_cost_center": "Dairy Farm - AIG",
        "aig_purpose_note": "probe (deleted)",
        "items": [{"item_code": "AIG-INV-FEED", "qty": 5,
                   "warehouse": "Dairy Farm Store - AIG",
                   "schedule_date": frappe.utils.today()}],
    })
    d.insert()
    probe = d.name
    log(f"  stock-item request OK: {d.name} (type={d.material_request_type})")
except Exception:
    log(f"  !! stock-item request failed: {frappe.get_traceback().strip().splitlines()[-1]}")

frappe.set_user("Administrator")
if probe:
    frappe.delete_doc("Material Request", probe, force=True, ignore_permissions=True)
    log(f"  cleaned probe {probe}")

log("")
log("STEP 5: which demo items are stock? (for the demo cast)")
for it in frappe.get_all("Item", fields=["item_code", "item_name", "is_stock_item", "disabled"]):
    bin_qty = frappe.db.get_value("Bin", {"item_code": it.item_code}, "actual_qty") or 0
    log(f"  {it.item_code} ({it.item_name}): stock={bool(it.is_stock_item)} onhand={bin_qty} disabled={it.disabled}")

log("")
log("STEP 6: the already-approved request with the wrong item")
rows = frappe.get_all(
    "Material Request",
    filters={"company": COMPANY, "docstatus": 1},
    fields=["name", "workflow_state", "owner"],
)
for r in rows:
    items = frappe.get_all("Material Request Item", filters={"parent": r.name}, pluck="item_code")
    log(f"  {r.name} state={r.workflow_state} owner={r.owner} items={items}")

log("")
log("DONE")
