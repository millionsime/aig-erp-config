# 146_committee_click_approval.py -- PRODUCTION UX fix (commits on success).
# Demo finding 2026-09-27: after the officer sent the PO to the committee, the
# committee member clicked the workflow button and was told to record a
# sign-off row FIRST - a two-step flow left over from the 2-of-3 design.
# With the single-approval rule the WORKFLOW CLICK ITSELF IS THE DECISION:
# when a member moves the PO out of 'Pending Committee Signoff' (Finalize
# Committee Decision / Forward to Tender Committee / Reject), that member's
# AIG Committee Signoff row is recorded automatically with the matching
# decision (Approve for Finalize/Forward, Reject for Reject). An existing row
# for the same member is reused/updated (CS Guard allows only one row per
# member); manually recorded rows keep working. Rejection still needs TWO
# distinct members: a lone Reject click records the row and asks for the
# second member. Sandbox constraints honored: no getattr, no flt,
# no str.format; previous state read from the DB (event stays
# "Before Save (Submitted Document)" = before_update_after_submit, which
# fires BEFORE validate_workflow).
import frappe


def log(*a):
    print(*a, flush=True)


MAJORITY = '''# AIG - PO Committee Majority (Purchase Order, Before Save (Submitted Document)).
# Committee rule (revised 2026-09-27, scripts 136 + 146): ONE committee member
# approves on behalf of all - and THE WORKFLOW CLICK IS THE APPROVAL. When a
# member moves the PO out of 'Pending Committee Signoff' (Finalize Committee
# Decision / Forward to Tender Committee / Reject), that member's sign-off row
# (AIG Committee Signoff) is recorded automatically with the matching decision;
# manually recorded rows are reused, so both paths coexist. Rejection still
# needs TWO distinct members: a lone Reject click records the member's row and
# asks for the second member. Above ETB 750,000 the upstream Material Request
# must be Enterprise-Head endorsed (Section 3.1 Bulky/Open-Tender
# precondition). Only fires on a STATE CHANGE out of the sign-off stage;
# plain edits inside the stage stay possible.
# NOTE: no getattr (sandbox forbids it) and no str.format - the previous state
# is read from the database, which still holds the pre-save state here.
prev_state = None
if doc.name and not doc.get("__islocal"):
    prev_state = frappe.db.get_value("Purchase Order", doc.name, "workflow_state")
state = doc.get("workflow_state")
if prev_state == "Pending Committee Signoff" and state != "Pending Committee Signoff":
    member = frappe.session.user
    decision = "Reject" if state == "Rejected" else "Approve"
    mine = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name,
                                   "committee_member": member},
                          pluck="name")
    if mine:
        frappe.db.set_value("AIG Committee Signoff", mine[0],
                            {"decision": decision,
                             "decision_date": frappe.utils.nowdate()},
                            update_modified=False)
    else:
        frappe.get_doc({"doctype": "AIG Committee Signoff",
                        "parent_po": doc.name, "decision": decision}).insert()
    approvals = []
    rejects = []
    rows = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name},
                          fields=["committee_member", "decision"])
    for r in rows:
        if r.committee_member not in approvals and r.committee_member not in rejects:
            if r.decision == "Approve":
                approvals.append(r.committee_member)
            elif r.decision == "Reject":
                rejects.append(r.committee_member)
    if state == "Rejected":
        if len(rejects) < 2:
            frappe.throw("AIG committee rule: a committee rejection needs "
                         "TWO members to click 'Reject' - your 'Reject' has "
                         "been recorded; only " + str(len(rejects)) +
                         " of 2 'Reject' sign-offs are recorded so far.")
    else:
        if len(rejects) >= 2:
            frappe.throw("AIG committee rule: 2 'Reject' sign-offs are recorded - "
                         "this Purchase Order must be Rejected by the committee.")
        if len(approvals) < 1:
            frappe.throw("AIG committee rule: one committee 'Approve' sign-off is "
                         "required - that member approves on behalf of all - but "
                         "no 'Approve' sign-off is recorded yet.")
        if (doc.grand_total or 0) > 750000:
            mrs = []
            for it in (doc.items or []):
                if it.get("material_request") and it.material_request not in mrs:
                    mrs.append(it.material_request)
            if not mrs:
                frappe.throw("AIG Bulky/Open Tender: this Purchase Order needs a "
                             "Material Request endorsed by the Enterprise Head "
                             "(no Material Request is referenced).")
            for mr in mrs:
                st = frappe.db.get_value("Material Request", mr, "workflow_state")
                if st not in ("Endorsed", "Approved"):
                    frappe.throw("AIG Bulky/Open Tender: Material Request " +
                                 mr + " is not yet endorsed by the Enterprise "
                                 "Head (state: " + str(st) + ").")
'''

maj = frappe.get_doc("Server Script", "AIG - PO Committee Majority")
maj.script = MAJORITY
maj.disabled = 0
if maj.doctype_event != "Before Save (Submitted Document)":
    maj.doctype_event = "Before Save (Submitted Document)"
maj.flags.ignore_permissions = True
maj.save(ignore_permissions=True)
log("AIG - PO Committee Majority updated: the workflow CLICK is the "
    "committee decision (auto-recorded sign-off; reject still needs 2 members)")
log(f"  doctype_event={maj.doctype_event} disabled={maj.disabled}")
frappe.clear_cache()
log("DONE 146")
