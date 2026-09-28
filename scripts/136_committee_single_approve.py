# 136_committee_single_approve.py -- PRODUCTION rule change (commits on success).
# Management decision 2026-09-27: ONE committee member approves on behalf of
# all - the 2-of-3 majority gate on "AIG - PO Committee Majority" is relaxed
# to a single distinct 'Approve' sign-off. Rejection semantics are unchanged
# (>= 2 'Reject' rows to reject / force-reject). Sandbox constraints honored:
# no getattr, no flt, no str.format; previous state read from the DB (same
# mechanics as the 133e canonical text; event stays "Before Save (Submitted
# Document)" = before_update_after_submit, which fires BEFORE validate_workflow).
import frappe


def log(*a):
    print(*a, flush=True)


MAJORITY = '''# AIG - PO Committee Majority (Purchase Order, Before Save (Submitted Document)).
# Committee rule (revised 2026-09-27, script 136): ONE committee member approves
# on behalf of all - a single distinct 'Approve' sign-off is enough for the PO
# to leave 'Pending Committee Signoff'. Rejection semantics are unchanged:
# 2 distinct 'Reject' rows are required to use the Rejected outcome, and
# 2 'Reject' rows force the Rejected outcome (they block any Finalize).
# Also enforces the Bulky/Open-Tender precondition: above ETB 750,000 the
# upstream Material Request must be Enterprise-Head endorsed (Section 3.1).
# Only fires on a STATE CHANGE out of the sign-off stage; plain edits inside
# the stage (fixing items, adding rows) stay possible.
# NOTE: no getattr (sandbox forbids it) and no str.format - the previous state
# is read from the database, which still holds the pre-save state here.
prev_state = None
if doc.name and not doc.get("__islocal"):
    prev_state = frappe.db.get_value("Purchase Order", doc.name, "workflow_state")
state = doc.get("workflow_state")
if prev_state == "Pending Committee Signoff" and state != "Pending Committee Signoff":
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
            frappe.throw("AIG committee rule: a committee rejection needs at least "
                         "2 'Reject' sign-offs; only " + str(len(rejects)) +
                         " recorded so far.")
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
log("AIG - PO Committee Majority rewritten: 1 committee Approve finalizes "
    "(reject rule unchanged: >= 2 Rejects)")
log(f"  doctype_event={maj.doctype_event} disabled={maj.disabled}")
frappe.clear_cache()
log("DONE 136")
