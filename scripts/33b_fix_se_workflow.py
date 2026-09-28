# AIG config - step 33b: CORRECT the "AIG Store Receiving" Stock Entry workflow for
# separation of duties. The Property Administration Expert must only ASSIGN bins
# (write), never POST stock. A distinct "Pending Posting" state is added and the
# General Store Keeper performs the posting for non-Main-Store receipts; the Main
# Store Administrator posts Main Store receipts. Updates the existing workflow in
# place (no delete). NO core edits.
import frappe
import traceback

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def get_or_create(dt, filters, values, label):
    name = frappe.db.get_value(dt, filters)
    if name:
        log("EXISTS", f"{label}: {name}")
        return name
    doc = frappe.get_doc(values)
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"{label}: {doc.name}")
        return doc.name
    except Exception:
        print(f"!! FAILED {label}")
        print(traceback.format_exc())
        return None


# new state + action required by the corrected flow
get_or_create("Workflow State", {"workflow_state_name": "Pending Posting"},
              {"doctype": "Workflow State", "workflow_state_name": "Pending Posting"},
              "Workflow State Pending Posting")
get_or_create("Workflow Action Master", {"workflow_action_name": "Post Receipt"},
              {"doctype": "Workflow Action Master", "workflow_action_name": "Post Receipt"},
              "Workflow Action Post Receipt")

SE_STATES = [
    {"state": "Draft", "doc_status": "0", "allow_edit": "AIG Store Keeper"},
    {"state": "Pending Inspection", "doc_status": "0", "allow_edit": "AIG Store Keeper"},
    {"state": "Pending GSK Approval", "doc_status": "0", "allow_edit": "AIG General Store Keeper"},
    {"state": "Pending Property Assignment", "doc_status": "0", "allow_edit": "AIG Property Admin Expert"},
    {"state": "Pending Posting", "doc_status": "0", "allow_edit": "AIG General Store Keeper"},
    {"state": "Pending Main Store Approval", "doc_status": "0", "allow_edit": "AIG Main Store Administrator"},
    {"state": "Posted", "doc_status": "1", "allow_edit": "System Manager"},
    {"state": "Rejected", "doc_status": "0", "allow_edit": "System Manager"},
]
SE_TRANSITIONS = [
    {"state": "Draft", "action": "Start Receiving", "next_state": "Pending Inspection",
     "allowed": "AIG Store Keeper", "condition": 'doc.purpose == "Material Receipt"'},
    {"state": "Pending Inspection", "action": "Record Inspection", "next_state": "Pending GSK Approval",
     "allowed": "AIG Store Keeper", "condition": None},
    {"state": "Pending Inspection", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG General Store Keeper", "condition": None},
    {"state": "Pending GSK Approval", "action": "Approve", "next_state": "Pending Property Assignment",
     "allowed": "AIG General Store Keeper", "condition": None},
    {"state": "Pending GSK Approval", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG General Store Keeper", "condition": None},
    # Property Expert assigns bins only - never posts.
    {"state": "Pending Property Assignment", "action": "Assign Bins", "next_state": "Pending Posting",
     "allowed": "AIG Property Admin Expert", "condition": "not doc.aig_needs_main_approval"},
    {"state": "Pending Property Assignment", "action": "Assign Bins", "next_state": "Pending Main Store Approval",
     "allowed": "AIG Property Admin Expert", "condition": "doc.aig_needs_main_approval == 1"},
    {"state": "Pending Property Assignment", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG General Store Keeper", "condition": None},
    # Posting is performed by the General Store Keeper (or Main Store Administrator).
    {"state": "Pending Posting", "action": "Post Receipt", "next_state": "Posted",
     "allowed": "AIG General Store Keeper", "condition": None},
    {"state": "Pending Main Store Approval", "action": "Final Approve & Post", "next_state": "Posted",
     "allowed": "AIG Main Store Administrator", "condition": None},
    {"state": "Pending Main Store Approval", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG Main Store Administrator", "condition": None},
    # Non-receipt movements (issue / transfer / adjustment) post directly.
    {"state": "Draft", "action": "Post Movement", "next_state": "Posted",
     "allowed": "AIG Store Keeper", "condition": 'doc.purpose != "Material Receipt"'},
]

name = "AIG Store Receiving"
if not frappe.db.exists("Workflow", name):
    log("FLAG", "Workflow AIG Store Receiving missing - run step 33 first")
else:
    wf = frappe.get_doc("Workflow", name)
    wf.set("states", [])
    wf.set("transitions", [])
    for s in SE_STATES:
        wf.append("states", s)
    for t in SE_TRANSITIONS:
        wf.append("transitions", {"state": t["state"], "action": t["action"],
                                 "next_state": t["next_state"], "allowed": t["allowed"],
                                 "condition": t.get("condition") or None})
    wf.flags.ignore_permissions = True
    wf.save(ignore_permissions=True)
    log("UPDATE", f"Workflow {name}: {len(SE_STATES)} states, {len(SE_TRANSITIONS)} transitions (SoD corrected)")

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP33B_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
