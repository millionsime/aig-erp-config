# 134b_majority_event.py -- PRODUCTION fix (commits on success).
# With the signoff states now submitting the PO on entry (doc_status 1), the
# committee stage operates on a SUBMITTED document: Before Validate no longer
# fires there, and on_update_after_submit (After Save) runs AFTER workflow
# validation - so the 2-of-3 majority gate never executed on Finalize /
# Forward / Reject actions (caught by the 134 acceptance run, S4/S5).
# The script must run on "Before Save (Submitted Document)"
# (= before_update_after_submit), which fires BEFORE validate_workflow and
# therefore still blocks the transition.
import frappe


def log(*a):
    print(*a, flush=True)


maj = frappe.get_doc("Server Script", "AIG - PO Committee Majority")
if maj.doctype_event != "Before Save (Submitted Document)":
    maj.doctype_event = "Before Save (Submitted Document)"
    maj.flags.ignore_permissions = True
    maj.save(ignore_permissions=True)
    log(f"  doctype_event -> {maj.doctype_event}")
else:
    log("  already on Before Save (Submitted Document)")
log(f"  disabled={maj.disabled}")
frappe.clear_cache()
log("DONE 134b")
