# 116_final_rehearsal_and_cleanup.py -- Definitive end-to-end rehearsal of the
# demo inventory flow, plus the fixes 114/115 exposed:
#   STEP 1: cancel+delete MAT-MR-2026-00005 (Approved MR carrying junk item
#           AIG-DEMO-123 "Chair" -- its SE can never post: no valuation).
#   STEP 2: disable junk items AIG-DEMO-123 and aabbaa so item search stops
#           offering them to demo users (user-flagged polish).
#   STEP 3: FULL ACT 1-3 REHEARSAL with the real demo item AIG-INV-FEED:
#           enduser.agro creates + submits the MR (Submit Request),
#           storeadmin.agro approves, head.agro approves => Approved.
#   STEP 4: ACT 4 SAVE-PATH TEST: storekeeper.agro insert()s the issue Stock
#           Entry with a clean payload (no row CC) => must succeed through
#           permission check + all AIG server scripts + workflow.
#   STEP 5: safety net: Administrator inserts SE with HO-poisoned row CC =>
#           "AIG - SE CC Normalize" must rewrite it to Dairy Farm - AIG.
#   STEP 6: delete all rehearsal docs (SE x2, MR + its workflow history) so
#           Saturday starts from a clean state. Junk items stay disabled.

import frappe
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
ENDUSER = "enduser.agro@aig.local"
STOREADMIN = "storeadmin.agro@aig.local"
HEAD = "head.agro@aig.local"
STOREKEEPER = "storekeeper.agro@aig.local"
DT = "Stock Entry"
ITEM = "AIG-INV-FEED"
WH = "Dairy Farm Store - AIG"
JUNK_ITEMS = ["AIG-DEMO-123", "aabbaa"]
JUNK_MRS = ["MAT-MR-2026-00005"]


def log(*a):
    print(*a, flush=True)


def delete_mr(name):
    if not frappe.db.exists("Material Request", name):
        log(f"  {name}: not present")
        return
    d = frappe.get_doc("Material Request", name)
    if d.docstatus == 1:
        frappe.set_user("Administrator")
        d.cancel()
        log(f"  {name}: cancelled")
    frappe.delete_doc("Material Request", name, ignore_permissions=True, force=True)
    log(f"  {name}: deleted")
    frappe.set_user("Administrator")
    try:  # v16: this log doctype may not exist -- best-effort cleanup only
        for h in frappe.get_all("Workflow Action History",
                                filters={"reference_name": name}, pluck="name"):
            frappe.delete_doc("Workflow Action History", h,
                              ignore_permissions=True, force=True)
    except Exception:
        pass


log("STEP 1: remove MR(s) carrying junk items")
for mr in JUNK_MRS:
    delete_mr(mr)

log("")
log("STEP 2: disable junk items")
for code in JUNK_ITEMS:
    if frappe.db.exists("Item", code):
        frappe.db.set_value("Item", code, "disabled", 1, update_modified=False)
        log(f"  disabled: {code}")
    else:
        log(f"  not found (skip): {code}")
frappe.clear_cache()
log("  cache cleared")

log("")
log("STEP 3: ACT 1-3 rehearsal -- approved MR for AIG-INV-FEED")
mr_name = None
try:
    frappe.set_user(ENDUSER)
    mr = frappe.new_doc("Material Request")
    mr.company = COMPANY
    mr.material_request_type = "Material Issue"
    mr.schedule_date = frappe.utils.add_days(frappe.utils.nowdate(), 2)
    mr.aig_budget_note = "Rehearsal for Saturday demo"
    # v16 Material Request Item has a single 'warehouse' column
    mr.append("items", {"item_code": ITEM, "qty": 2, "schedule_date":
                        mr.schedule_date, "warehouse": WH})
    mr.insert()
    mr_name = mr.name
    log(f"  created: {mr_name} (state={mr.workflow_state}, type={mr.material_request_type})")
    apply_workflow(mr, "Submit Request")
    log(f"  enduser Submit Request -> {mr.workflow_state}")
    frappe.set_user(STOREADMIN)
    mr = frappe.get_doc("Material Request", mr_name)
    apply_workflow(mr, "Approve")
    log(f"  storeadmin Approve     -> {mr.workflow_state}")
    frappe.set_user(HEAD)
    mr = frappe.get_doc("Material Request", mr_name)
    apply_workflow(mr, "Approve")
    log(f"  head Approve           -> {mr.workflow_state}")
    frappe.set_user(ENDUSER)
    final = frappe.get_doc("Material Request", mr_name)
    log(f"  FINAL MR state={final.workflow_state} docstatus={final.docstatus}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  REHEARSAL FAILED: {tail[-1] if tail else '?'}")

log("")
log("STEP 4: ACT 4 save-path test as storekeeper (clean payload)")
name_se1 = None
try:
    frappe.set_user(STOREKEEPER)
    se = frappe.new_doc(DT)
    se.company = COMPANY
    se.stock_entry_type = "Material Issue"
    se.purpose = "Material Issue"
    se.from_warehouse = WH
    se.aig_material_request = mr_name
    se.append("items", {"item_code": ITEM, "qty": 2, "basic_rate": 40,
                        "s_warehouse": WH})
    se.insert()
    name_se1 = se.name
    log(f"  INSERT OK: {name_se1}")
    log(f"    workflow_state = {se.workflow_state}")
    log(f"    header aig_cost_center = {se.aig_cost_center!r}")
    log(f"    row cost_centers = {[d.cost_center for d in se.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")

log("")
log("STEP 5: safety net -- Administrator insert with HO-poisoned row")
name_se2 = None
try:
    frappe.set_user("Administrator")
    se = frappe.new_doc(DT)
    se.company = COMPANY
    se.stock_entry_type = "Material Issue"
    se.purpose = "Material Issue"
    se.from_warehouse = WH
    se.aig_material_request = mr_name
    se.append("items", {"item_code": ITEM, "qty": 1, "basic_rate": 40,
                        "s_warehouse": WH, "cost_center": "Head Office - AIG"})
    se.insert(ignore_permissions=True)
    name_se2 = se.name
    log(f"  INSERT OK: {name_se2}")
    log(f"    header aig_cost_center = {se.aig_cost_center!r} (expect Dairy)")
    log(f"    row cost_centers = {[d.cost_center for d in se.items]} (expect Dairy)")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")

log("")
log("STEP 6: clean up all rehearsal docs")
frappe.set_user("Administrator")
for n in (name_se1, name_se2):
    if n and frappe.db.exists(DT, n):
        frappe.delete_doc(DT, n, ignore_permissions=True, force=True)
        log(f"  deleted test SE {n}")
if mr_name and frappe.db.exists("Material Request", mr_name):
    delete_mr(mr_name)

log("")
log("VERDICT: STEP 4 INSERT OK => the browser Save works. Junk items disabled; "
    "junk MR removed. Hard-refresh (Ctrl+Shift+R) and run Acts 1-4 with "
    "AIG-INV-FEED.")
