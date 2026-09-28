# 148_committee_reject_guard.py -- PRODUCTION UX fix, part 2 (commits on
# success). apply_workflow reaches the Rejected state (doc_status 2) via
# doc.cancel(), which never fires before_update_after_submit - so the lone
# "Reject" click bypassed the two-member rule entirely (caught by probe 147
# C2). Fix = two scripts working together:
#   1) "AIG - PO Committee Majority" (Before Save (Submitted Document)):
#      now only guards NON-Rejected exits - the clicking member's Approve row
#      is auto-recorded (click = approval, one member on behalf of all).
#   2) NEW "AIG - PO Committee Reject Guard" (Before Cancel on Purchase
#      Order): enforces the TWO-member rejection rule on the cancel path.
#      The sandbox removes frappe.db.commit from Server Scripts (verified
#      empirically), so a bounced click's auto-recorded row could never
#      survive the rollback - rejections therefore use the sign-off ROW
#      flow: each member records their 'Reject' row (AIG Committee Signoff),
#      and the 'Reject' click is only accepted once TWO rows exist. The
#      messages tell the member exactly what is missing at each step.
# No getattr, no flt, no str.format anywhere (sandbox).
import frappe


def log(*a):
    print(*a, flush=True)


MAJORITY = '''# AIG - PO Committee Majority (Purchase Order, Before Save (Submitted Document)).
# Committee rule (revised 2026-09-27, scripts 136 + 146 + 148): ONE committee
# member approves on behalf of all - and THE WORKFLOW CLICK IS THE APPROVAL.
# When a member moves the PO out of 'Pending Committee Signoff' (Finalize
# Committee Decision / Forward to Tender Committee), that member's sign-off
# row (AIG Committee Signoff) is recorded automatically as 'Approve'; an
# existing row for the same member is reused, so manually recorded rows keep
# working. REJECTIONS are handled by "AIG - PO Committee Reject Guard"
# (Before Cancel) because the Rejected state is reached through document
# cancellation, which does not run this event. Above ETB 750,000 the upstream
# Material Request must be Enterprise-Head endorsed (Bulky/Open-Tender
# precondition, Section 3.1). Only fires on a STATE CHANGE out of the
# sign-off stage; plain edits inside the stage stay possible.
# NOTE: no getattr (sandbox forbids it) and no str.format - the previous
# state is read from the database, which still holds the pre-save state here.
prev_state = None
if doc.name and not doc.get("__islocal"):
    prev_state = frappe.db.get_value("Purchase Order", doc.name, "workflow_state")
state = doc.get("workflow_state")
if (prev_state == "Pending Committee Signoff"
        and state != "Pending Committee Signoff" and state != "Rejected"):
    member = frappe.session.user
    mine = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name,
                                   "committee_member": member},
                          pluck="name")
    if mine:
        frappe.db.set_value("AIG Committee Signoff", mine[0],
                            {"decision": "Approve",
                             "decision_date": frappe.utils.nowdate()},
                            update_modified=False)
    else:
        frappe.get_doc({"doctype": "AIG Committee Signoff",
                        "parent_po": doc.name,
                        "decision": "Approve"}).insert()
    rejects = []
    rows = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name},
                          fields=["committee_member", "decision"])
    for r in rows:
        if r.decision == "Reject" and r.committee_member not in rejects:
            rejects.append(r.committee_member)
    if len(rejects) >= 2:
        frappe.throw("AIG committee rule: 2 'Reject' sign-offs are recorded - "
                     "this Purchase Order must be Rejected by the committee.")
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

REJECT_GUARD = '''# AIG - PO Committee Reject Guard (Purchase Order, Before Cancel).
# The committee's 'Reject' click lands the PO in 'Rejected' (doc_status 2)
# via document cancellation - an event where "AIG - PO Committee Majority"
# (Before Save (Submitted Document)) never runs. This guard enforces the
# TWO-member rejection rule here: each member first records their 'Reject'
# row (AIG Committee Signoff) - the sandbox strips frappe.db.commit from
# Server Scripts, so rows recorded during a bounced click would vanish with
# the rollback; the row flow is the reliable path. Messages name exactly
# what is missing at each step. Administrator cancels (housekeeping,
# cleanup) skip the rule. No getattr / flt / str.format (sandbox).
prev_state = None
if doc.name and not doc.get("__islocal"):
    prev_state = frappe.db.get_value("Purchase Order", doc.name, "workflow_state")
if (prev_state == "Pending Committee Signoff"
        and frappe.session.user != "Administrator"):
    member = frappe.session.user
    mine = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name,
                                   "committee_member": member,
                                   "decision": "Reject"},
                          pluck="name")
    rejects = []
    rows = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name,
                                   "decision": "Reject"},
                          fields=["committee_member"])
    for r in rows:
        if r.committee_member not in rejects:
            rejects.append(r.committee_member)
    if not mine:
        frappe.throw("AIG committee rule: a committee rejection needs TWO "
                     "members. Record your 'Reject' sign-off first (AIG "
                     "Committee Signoff -> Add), then click 'Reject' again. "
                     + str(len(rejects)) + " of 2 'Reject' sign-offs are "
                     "recorded.")
    if len(rejects) < 2:
        frappe.throw("AIG committee rule: your 'Reject' sign-off is "
                     "recorded - one MORE committee member must record "
                     "their 'Reject' before this Purchase Order can be "
                     "rejected. " + str(len(rejects)) + " of 2 recorded.")
'''

maj = frappe.get_doc("Server Script", "AIG - PO Committee Majority")
maj.script = MAJORITY
maj.disabled = 0
if maj.doctype_event != "Before Save (Submitted Document)":
    maj.doctype_event = "Before Save (Submitted Document)"
maj.flags.ignore_permissions = True
maj.save(ignore_permissions=True)
log("1) AIG - PO Committee Majority: non-Rejected exits only "
    "(click = Approve on behalf of all)")

if frappe.db.exists("Server Script", "AIG - PO Committee Reject Guard"):
    rg = frappe.get_doc("Server Script", "AIG - PO Committee Reject Guard")
    rg.script = REJECT_GUARD
    rg.disabled = 0
    if rg.reference_doctype != "Purchase Order":
        rg.reference_doctype = "Purchase Order"
    if rg.doctype_event != "Before Cancel":
        rg.doctype_event = "Before Cancel"
    rg.flags.ignore_permissions = True
    rg.save(ignore_permissions=True)
    log("2) AIG - PO Committee Reject Guard: updated (Before Cancel)")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - PO Committee Reject Guard",
        "script_type": "DocType Event", "reference_doctype": "Purchase Order",
        "doctype_event": "Before Cancel", "disabled": 0,
        "script": REJECT_GUARD, "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("2) AIG - PO Committee Reject Guard: created (Before Cancel)")

frappe.clear_cache()
log("DONE 148")
