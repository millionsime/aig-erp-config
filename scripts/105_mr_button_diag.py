# 105_mr_button_diag.py -- Why "only Save, no Submit Request": check the
# end user's saved MR drafts for row cost_center values outside her scope,
# and whether workflow transitions resolve for her on the saved docs.

import frappe

COMPANY = "Adama Investment Group"
U = "enduser.agro@aig.local"


def log(*a):
    print(*a, flush=True)


log("1) AIG - MR Item Cost Center Sync (script text)")
log(frappe.db.get_value("Server Script", "AIG - MR Item Cost Center Sync", "script") or "(missing)")

log("")
log("2) end user's saved Material Requests (row cost centers)")
frappe.set_user("Administrator")
mrs = frappe.get_all(
    "Material Request",
    filters={"owner": U, "company": COMPANY},
    fields=["name", "workflow_state", "docstatus", "aig_cost_center", "material_request_type"],
    order_by="creation desc",
    limit=10,
)
for m in mrs:
    rows = frappe.get_all(
        "Material Request Item",
        filters={"parent": m.name},
        fields=["item_code", "qty", "warehouse", "cost_center"],
    )
    log(f"  {m.name} state={m.workflow_state} docstatus={m.docstatus} hdrCC={m.aig_cost_center} type={m.material_request_type}")
    for r in rows:
        log(f"    row: {r.item_code} x{r.qty} wh={r.warehouse} rowCC={r.cost_center}")

log("")
log("3) workflow transitions as the end user on each saved draft")
from frappe.model.workflow import get_transitions

for m in mrs:
    if m.docstatus != 0:
        continue
    frappe.set_user(U)
    doc = frappe.get_doc("Material Request", m.name)
    try:
        ts = get_transitions(doc)
        names = [f"{t.action}->{t.to_state}" for t in ts]
        log(f"  {m.name}: transitions={names or '(EMPTY)'}")
    except Exception:
        log(f"  {m.name}: transitions FAIL: {frappe.get_traceback().strip().splitlines()[-1][:120]}")
frappe.set_user("Administrator")

log("")
log("4) does SHE have submit/create perms needed for the action?")
frappe.set_user(U)
log(f"  MR create: {frappe.has_permission('Material Request', 'create', user=U, throw=False)}")
log(f"  MR read:   {frappe.has_permission('Material Request', 'read', user=U, throw=False)}")
frappe.set_user("Administrator")
