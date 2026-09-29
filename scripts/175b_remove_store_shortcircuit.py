# 175b_remove_store_shortcircuit.py -- PATCH (commits on success): remove the
# 'Pending Store Review --Approve--> Approved' transition added by 175. It
# short-circuits the ORIGINAL Material Issue route (store Approve must go to
# Pending Enterprise Approval, then the Enterprise Head approves). The
# end-user Purchase route keeps its own conditional 'Approve & Assign'.
import frappe

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")
w = frappe.get_doc("Workflow", "AIG Stock Request Approval")
before = [(t.state, t.action, t.next_state) for t in w.transitions]
log("before:", before)
kept = []
removed = 0
for t in w.transitions:
    if (t.state == "Pending Store Review" and t.action == "Approve"
            and t.next_state == "Approved"):
        removed += 1
        continue
    kept.append(t)
if not removed:
    log("nothing to remove - already clean")
else:
    w.transitions = []
    for t in kept:
        w.append("transitions", {
            "state": t.state, "action": t.action, "next_state": t.next_state,
            "allowed": t.allowed, "condition": t.condition,
        })
    w.save(ignore_permissions=True)
    log("removed", removed, "short-circuit row(s)")
    log("after:", [(t.state, t.action, t.next_state) for t in kept])
frappe.clear_cache()
log("DONE 175b")
