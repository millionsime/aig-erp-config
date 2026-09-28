# 133d2_wf_dump.py -- READ-ONLY dump of workflow transitions + child states.
import frappe


def log(*a):
    print(*a, flush=True)


for wf_name in ["AIG Stock Request Approval", "AIG Procurement Approval",
                "AIG Payment Approval"]:
    wfd = frappe.get_doc("Workflow", wf_name)
    log(f"=== {wf_name} (state_field={wfd.workflow_state_field}) ===")
    for s in wfd.states:
        log(f"  STATE {s.state:42s} doc_status={s.doc_status} allow_edit={s.allow_edit}")
    for t in wfd.transitions:
        src = {x.state: x.doc_status for x in wfd.states}.get(t.state, "?")
        dst = {x.state: x.doc_status for x in wfd.states}.get(t.next_state, "?")
        flag = "  <<INVALID 0->2" if src in (0, "0") and dst in (2, "2") else ""
        flag += "  <<INVALID 1->0" if src in (1, "1") and dst in (0, "0") else ""
        log(f"  T{t.idx:>2} {t.state} ({src}) --[{t.action}]({t.allowed})--> "
            f"{t.next_state} ({dst}) cond={t.condition!r}{flag}")
    log("")
log("READ-ONLY DUMP DONE")
