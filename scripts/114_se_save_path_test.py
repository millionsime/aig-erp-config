# 114_se_save_path_test.py -- End-to-end proof on the REAL save path
# (doc.insert(), not has_permission probes):
#   TEST 1: as storekeeper.agro, insert the exact payload the browser sends
#           after the new intercept (rows have NO cost center). Must pass
#           check_permission('create') + all AIG server scripts + workflow.
#   TEST 2: as Administrator, insert with a Head-Office-poisoned row CC. The
#           "AIG - SE CC Normalize" Before-Validate script must rewrite it to
#           the enterprise CC (safety net for anything that slips through).
# Both test docs are deleted again -- the site stays as it was.

import frappe

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"
DT = "Stock Entry"
WH = "Dairy Farm Store - AIG"
MR = "MAT-MR-2026-00005"

CREATED = []


def log(*a):
    print(*a, flush=True)


def mr_item():
    row = frappe.get_all("Material Request Item",
                         filters={"parent": MR}, fields=["item_code", "qty"],
                         limit=1)
    return (row[0].item_code, row[0].qty) if row else ("AIG-INV-FEED", 1)


def build(as_user, row_cc):
    frappe.set_user(as_user)
    doc = frappe.new_doc(DT)
    doc.company = COMPANY
    doc.stock_entry_type = "Material Issue"
    doc.purpose = "Material Issue"
    doc.from_warehouse = WH
    doc.aig_material_request = MR
    item = {"item_code": ITEM_CODE, "qty": 1, "basic_rate": 40,
            "s_warehouse": WH}
    if row_cc:
        item["cost_center"] = row_cc
    doc.append("items", item)
    return doc


def cleanup(docname):
    frappe.set_user("Administrator")
    if docname and frappe.db.exists(DT, docname):
        d = frappe.get_doc(DT, docname)
        if d.docstatus == 1:
            d.cancel()
        frappe.delete_doc(DT, docname, ignore_permissions=True, force=True)
        log(f"  cleaned up test doc {docname}")


ITEM_CODE, MR_QTY = mr_item()
log(f"approved MR {MR}: item={ITEM_CODE} qty={MR_QTY}")

log("")
log("TEST 1: real insert() as storekeeper.agro with CLEAN payload (no row CC)")
name1 = None
try:
    doc = build(U, None)
    doc.insert(ignore_permissions=False)
    name1 = doc.name
    log(f"  INSERT OK: {name1}")
    log(f"    workflow_state    = {doc.workflow_state}")
    log(f"    header aig_cost_center = {doc.aig_cost_center!r}")
    log(f"    row cost_centers  = {[d.cost_center for d in doc.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")
finally:
    cleanup(name1)

log("")
log("TEST 2: real insert() as Administrator with HEAD-OFFICE-poisoned row")
name2 = None
try:
    doc = build("Administrator", "Head Office - AIG")
    doc.insert(ignore_permissions=True)
    name2 = doc.name
    log(f"  INSERT OK: {name2}")
    log(f"    header aig_cost_center = {doc.aig_cost_center!r} (expect Dairy Farm - AIG)")
    log(f"    row cost_centers  = {[d.cost_center for d in doc.items]} "
        f"(expect normalized to Dairy)")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")
finally:
    cleanup(name2)

log("")
log("VERDICT: TEST 1 OK => storekeeper can save the issue Stock Entry "
    "(hard-refresh Ctrl+Shift+R first). TEST 2 normalized => safety net works.")
