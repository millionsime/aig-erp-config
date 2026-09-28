# 150_full_mr_chain.py -- READ-ONLY: complete transition map of the MR
# workflow (AIG Stock Request Approval) + who can act on the live demo MR
# MAT-MR-2026-00014 right now. Creates nothing.
import frappe
from frappe.model.workflow import get_transitions, get_workflow


def log(*a):
    print(*a, flush=True)


log("full transition map: AIG Stock Request Approval")
for t in frappe.get_all("Workflow Transition",
                        filters={"parent": "AIG Stock Request Approval"},
                        fields=["state", "action", "next_state", "allowed",
                                "condition"],
                        order_by="idx"):
    log(f"  {t.state} --[{t.action}]--> {t.next_state} "
        f"allowed={t.allowed} cond={t.condition!r}")

log("")
log("state doc_status map")
wf = get_workflow("Material Request")
for s in wf.states:
    log(f"  {s.state}: doc_status={s.doc_status} "
        f"allow_edit={s.allow_edit!r}")

log("")
log("material_request_type of the demo MRs")
for n in ["MAT-MR-2026-00014", "MAT-MR-2026-00011", "MAT-MR-2026-00003"]:
    log(f"  {n}: type="
        f"{frappe.db.get_value('Material Request', n, 'material_request_type')!r}")

log("")
log("who has transitions on MAT-MR-2026-00014 right now?")
doc = frappe.get_doc("Material Request", "MAT-MR-2026-00014")
for u in ["storekeeper.agro@aig.local", "storeadmin.agro@aig.local",
          "mainstore@aig.local", "inv.admin@aig.local",
          "procurement.agro@aig.local", "enduser.agro@aig.local"]:
    frappe.set_user(u)
    try:
        ts = [f"{t.action}->{t.next_state}" for t in get_transitions(doc)]
        log(f"  {u}: {ts or 'NONE'}")
    finally:
        frappe.set_user("Administrator")
log("DONE 150")
