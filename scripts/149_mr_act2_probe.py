# 149_mr_act2_probe.py -- READ-ONLY diagnosis of the Act 2 symptom: the
# Procurement Officer sees NO workflow action button on the enduser-created
# Material Request. Dumps the recent MRs and, as procurement.agro, runs the
# exact checks the UI runs (doc read + get_transitions + per-transition
# role/condition evaluation). Creates nothing, deletes nothing.
import frappe
from frappe.model.workflow import get_transitions, get_workflow


def log(*a):
    print(*a, flush=True)


OFFICER = "procurement.agro@aig.local"

log("1) recent Material Requests")
mrs = frappe.get_all("Material Request", filters={"docstatus": ["<", 2]},
                     fields=["name", "owner", "workflow_state", "docstatus",
                             "aig_cost_center",
                             "aig_estimated_total", "transaction_date"],
                     order_by="creation desc", limit_page_length=6)
for m in mrs:
    log(f"  {m.name} owner={m.owner} state={m.workflow_state!r} "
        f"docstatus={m.docstatus}")
    log(f"    aig_cost_center={m.aig_cost_center!r} "
        f"estimate={m.aig_estimated_total!r}")
    rows = frappe.get_all("Material Request Item",
                          filters={"parent": m.name},
                          fields=["item_code", "qty", "rate", "warehouse",
                                  "cost_center"])
    for r in rows:
        wh_cc = frappe.db.get_value("Warehouse", r.warehouse,
                                    "aig_cost_center") if r.warehouse else None
        log(f"    row: {r.item_code} qty={r.qty} rate={r.rate} "
            f"wh={r.warehouse!r} wh.aig_cost_center={wh_cc!r} "
            f"row.cost_center={r.cost_center!r}")

log("")
log("2) system setting: apply_strict_user_permissions = "
    f"{frappe.get_system_settings('apply_strict_user_permissions')}")

log("")
log(f"3) as {OFFICER}: doc read + transitions per MR")
for m in mrs:
    doc = frappe.get_doc("Material Request", m.name)
    frappe.set_user(OFFICER)
    try:
        read_ok = frappe.has_permission("Material Request", "read", doc=doc)
        trans = []
        if read_ok:
            wf = get_workflow("Material Request")
            for t in get_transitions(doc, wf):
                trans.append(f"{t.action} -> {t.next_state} (allowed={t.allowed})")
        log(f"  {m.name}: read={read_ok} transitions={trans or 'NONE'}")
    finally:
        frappe.set_user("Administrator")

log("")
log("4) raw transition definitions on Draft (role + condition)")
for t in frappe.get_all("Workflow Transition",
                        filters={"parent": "AIG Stock Request Approval",
                                 "state": "Draft"},
                        fields=["action", "next_state", "allowed",
                                "condition"]):
    log(f"  --[{t.action}]--> {t.next_state} allowed={t.allowed} "
        f"cond={t.condition!r}")

log("")
log("5) officer roles + Cost Center user perms (sanity)")
log(f"  roles={sorted(frappe.get_roles(OFFICER))}")
rows = frappe.get_all("User Permission", filters={"user": OFFICER},
                      fields=["allow", "for_value", "applicable_for"])
for r in rows:
    log(f"  UP allow={r.allow} for_value={r.for_value} "
        f"applicable_for={r.applicable_for}")
log("DONE 149")
