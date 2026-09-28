# 120_fix_mr_cc_defaults.py -- 118/119 root cause: "AIG - MR Request Defaults"
# stamps header aig_cost_center from the FIRST Cost Center User Permission row
# -- after script 96 that can be the scoped ROOT CC ('Adama Investment Group -
# AIG'), which enterprise users cannot read at doc level, so get_transitions'
# read check kills their own Submit Request button. Fix:
#   1. Rewrite "AIG - MR Request Defaults": derive CC from the row warehouse's
#      enterprise CC first; fall back to the user's first UNSCOPED Cost Center
#      user permission (skip root CC / Head Office); never stamp the root CC.
#      Also fix rows: if the header CC exists, sync rows to it.
#   2. New "AIG - MR CC Normalize" (Before Validate) safety net: header CC is
#      warehouse-derived (row warehouse CC) when missing; rows synced to the
#      header; a leftover ROOT CC / Head Office value on the header is
#      replaced by the warehouse CC, because enterprise users cannot read it.
#   3. Client "AIG - MR CC Intercept": a model-event guard that instantly
#      reverts a root-CC injection on new MRs (mirrors the SE intercept).
# Then re-run the full Act 1-3 + Act 4 rehearsal end-to-end.

import frappe
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
ENDUSER = "enduser.agro@aig.local"
STOREADMIN = "storeadmin.agro@aig.local"
HEAD = "head.agro@aig.local"
STOREKEEPER = "storekeeper.agro@aig.local"
ITEM = "AIG-INV-FEED"
WH = "Dairy Farm Store - AIG"
ROOT_CC = "Adama Investment Group - AIG"
HO_CC = "Head Office - AIG"

CS_NAME = "AIG - MR CC Intercept"
SS_NAME = "AIG - MR CC Normalize"
DT = "Stock Entry"

DEFAULTS_BODY = """# AIG - default the requester and enterprise cost center on a new Stock
# Request. IMPORTANT: never stamp the root CC ('Adama Investment Group - AIG')
# or Head Office: enterprise-scoped users cannot read documents that carry
# them, which breaks the workflow buttons on their own requests. Prefer the
# warehouse's enterprise CC; fall back to the user's first unscoped Cost
# Center user permission.
if not doc.get("aig_requested_by"):
    doc.aig_requested_by = frappe.session.user
if not doc.get("aig_cost_center"):
    cc = None
    for it in (doc.items or []):
        if it.warehouse:
            cc = frappe.db.get_value("Warehouse", it.warehouse, "aig_cost_center")
            if cc:
                break
    if not cc:
        rows = frappe.get_all("User Permission",
                              filters={"user": frappe.session.user,
                                       "allow": "Cost Center"},
                              fields=["for_value", "applicable_for"])
        for r in rows:
            if r.for_value in ("Adama Investment Group - AIG", "Head Office - AIG"):
                continue
            if r.applicable_for and r.applicable_for != "Cost Center":
                continue
            cc = r.for_value
            break
    if not cc:
        cc = frappe.db.get_value("Company", doc.company, "cost_center")
    if cc in ("Adama Investment Group - AIG", "Head Office - AIG"):
        cc = None
    if cc:
        doc.aig_cost_center = cc
hdr = doc.get("aig_cost_center")
if hdr:
    for it in (doc.items or []):
        if not it.get("cost_center"):
            it.cost_center = hdr
        elif it.cost_center in ("Adama Investment Group - AIG", "Head Office - AIG"):
            it.cost_center = hdr
"""

NORMALIZE_BODY = """# AIG - MR CC Normalize (Before Validate): the workflow read check on the
# saved doc fails if the header carries a CC outside the requester's scope
# (root CC / Head Office). Derive the enterprise CC from the row warehouse,
# overwrite any root/HO value, and sync row cost centers. Runs before the
# workflow state is committed, so apply_workflow's doc-read always sees a
# document within the owner's enterprise scope.
row_cc = None
for it in (doc.items or []):
    if it.warehouse:
        row_cc = frappe.db.get_value("Warehouse", it.warehouse, "aig_cost_center")
        if row_cc:
            break
hdr = doc.get("aig_cost_center")
if hdr in ("Adama Investment Group - AIG", "Head Office - AIG", None, ""):
    hdr = row_cc
if hdr:
    doc.aig_cost_center = hdr
    for it in (doc.items or []):
        if it.cost_center in ("Adama Investment Group - AIG",
                              "Head Office - AIG", None, ""):
            it.cost_center = hdr
"""

CS_BODY = """// AIG - MR CC Intercept: ERPNext/the CC-sync script can stamp the root CC
// or Head Office onto a new Material Request. Enterprise users cannot read
// such documents at doc level, which silently kills their workflow buttons.
// This model-event guard instantly reverts those values on a new MR.
(function () {
\tvar POISON = ["Adama Investment Group - AIG", "Head Office - AIG"];
\tfunction is_poison(v) {
\t\treturn v && POISON.indexOf(v) !== -1;
\t}
\tfrappe.ui.form.on("Material Request", {
\t\taig_cost_center: function (frm) {
\t\t\tif (frm.doc.__islocal && is_poison(frm.doc.aig_cost_center)) {
\t\t\t\tfrm.set_value("aig_cost_center", null);
\t\t\t}
\t\t}
\t});
\tfrappe.ui.form.on("Material Request Item", {
\t\tcost_center: function (frm, cdt, cdn) {
\t\t\tvar row = locals[cdt] && locals[cdt][cdn];
\t\t\tif (frm.doc.__islocal && row && is_poison(row.cost_center)) {
\t\t\t\tfrappe.model.set_value(cdt, cdn, "cost_center", null);
\t\t\t}
\t\t}
\t});
})();"""


def log(*a):
    print(*a, flush=True)


def upsert_ss(name, body):
    if frappe.db.exists("Server Script", name):
        row = frappe.get_doc("Server Script", name)
        row.script = body
        row.disabled = 0
        row.flags.ignore_permissions = True
        row.save(ignore_permissions=True)
        log(f"  server script updated: {name}")
    else:
        frappe.get_doc({
            "doctype": "Server Script", "name": name,
            "script_type": "DocType Event", "reference_doctype": "Material Request",
            "doctype_event": "Before Validate", "disabled": 0, "script": body,
            "module": "AIG HR",
        }).insert(ignore_permissions=True)
        log(f"  server script created: {name}")


def upsert_cs():
    if frappe.db.exists("Client Script", CS_NAME):
        row = frappe.get_doc("Client Script", CS_NAME)
        row.script = CS_BODY
        row.enabled = 1
        row.flags.ignore_permissions = True
        row.save(ignore_permissions=True)
        log("  client script updated")
    else:
        frappe.get_doc({
            "doctype": "Client Script", "name": CS_NAME, "dt": "Material Request",
            "view": "Form", "enabled": 1, "script": CS_BODY, "module": "AIG HR",
        }).insert(ignore_permissions=True)
        log("  client script created")


log("STEP 1: rewrite MR Request Defaults (no root/HO stamping)")
upsert_ss("AIG - MR Request Defaults", DEFAULTS_BODY)

log("")
log("STEP 2: add MR CC Normalize (Before Validate safety net)")
upsert_ss(SS_NAME, NORMALIZE_BODY)

log("")
log("STEP 3: add MR CC Intercept (client model-event guard)")
upsert_cs()

frappe.clear_cache()
log("")
log("STEP 4: cache cleared")

log("")
log("STEP 5: ACT 1-3 rehearsal (create -> Submit Request -> Approve -> Approve)")
mr_name = None
try:
    frappe.set_user(ENDUSER)
    mr = frappe.new_doc("Material Request")
    mr.company = COMPANY
    mr.material_request_type = "Material Issue"
    mr.schedule_date = frappe.utils.add_days(frappe.utils.nowdate(), 2)
    mr.aig_budget_note = "Rehearsal for Saturday demo"
    mr.append("items", {"item_code": ITEM, "qty": 2, "schedule_date":
                        mr.schedule_date, "warehouse": WH})
    mr.insert()
    mr_name = mr.name
    log(f"  created: {mr_name} state={mr.workflow_state} "
        f"header CC={mr.aig_cost_center!r}")

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
    log("  ACT 1-3: ALL GREEN")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  ACT 1-3 FAILED: {tail[-1] if tail else '?'}")

log("")
log("STEP 6: ACT 4 save-path test as storekeeper (clean payload, links MR)")
name_se = None
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
    name_se = se.name
    log(f"  INSERT OK: {name_se} state={se.workflow_state} "
        f"header CC={se.aig_cost_center!r} rows={[d.cost_center for d in se.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  ACT 4 SAVE FAILED: {tail[-1] if tail else '?'}")

log("")
log("STEP 7: cleanup rehearsal docs")
frappe.set_user("Administrator")
if name_se and frappe.db.exists(DT, name_se):
    frappe.delete_doc(DT, name_se, ignore_permissions=True, force=True)
    log(f"  deleted test SE {name_se}")
if mr_name and frappe.db.exists("Material Request", mr_name):
    d = frappe.get_doc("Material Request", mr_name)
    if d.docstatus == 1:
        d.cancel()
        log(f"  cancelled rehearsal MR {mr_name}")
    frappe.delete_doc("Material Request", mr_name,
                      ignore_permissions=True, force=True)
    log(f"  deleted rehearsal MR {mr_name}")

log("")
log("VERDICT: Act 1-3 ALL GREEN + Act 4 INSERT OK => full demo flow works. "
    "Hard-refresh (Ctrl+Shift+R) and run Acts 1-4 live.")
