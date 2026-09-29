# 175_enduser_purchase_policy.py -- POLICY FLIP (commits on success).
# End Users may now INITIATE Purchase requests (management decision for the
# client demo). New route on Material Request:
#   End User --Submit Purchase Request--> Pending Head Approval (NEW state)
#   Enterprise Head --Approve--> Pending Store Review
#   Store Admin sets 'Assigned Procurement Officer', then --Approve & Assign--> Approved
# Officer-raised Purchase routes (<=750k direct, >750k endorsement) and the
# End-User Material Issue (Model 19) store route are UNCHANGED.
# Also: disables the two phase-1 guard scripts that forced End Users to
# Material Issue, adds a scope guard (Purchase only, for end users), adds the
# assignment custom field, and grants Main Store Administrator write on MR.
import frappe
import json

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")

# ---------------------------------------------------------------- 1. field
log("== 1. custom field: aig_assigned_procurement_officer")
if not frappe.db.exists("Custom Field", {"dt": "Material Request",
                                         "fieldname": "aig_assigned_procurement_officer"}):
    frappe.get_doc({
        "doctype": "Custom Field", "dt": "Material Request",
        "fieldname": "aig_assigned_procurement_officer",
        "label": "Assigned Procurement Officer", "fieldtype": "Link",
        "options": "User", "insert_after": "aig_budget_note",
        "read_only": 0, "allow_on_submit": 1,
        "description": "Set by the Store Administrator when approving the request",
    }).insert(ignore_permissions=True)
    log("   created (allow_on_submit=1)")
else:
    cf = frappe.get_doc("Custom Field", {"dt": "Material Request",
                                         "fieldname": "aig_assigned_procurement_officer"})
    cf.allow_on_submit = 1
    cf.read_only = 0
    cf.save(ignore_permissions=True)
    log("   exists -> allow_on_submit=1, editable")

# ------------------------------------------------- 2. disable type guards
log("== 2. disable End-User type guards (policy flip)")
for name in ["AIG - MR End User Type Default", "AIG - MR End User Type Guard"]:
    ss = frappe.get_doc("Server Script", name)
    if not ss.disabled:
        ss.disabled = 1
        ss.save(ignore_permissions=True)
        log("   disabled:", name)
    else:
        log("   already disabled:", name)

# ----------------------------------------------------- 3. scope guard
log("== 3. scope guard: AIG - MR End User Purchase Scope (Before Validate)")
scope_script = '''# AIG - End-User Purchase Scope. With end users initiating Purchase
# requests (2026-09 policy flip), they may only use Purchase or Material
# Issue; the exotic types (Manufacture/Reception/Transfer/Subcontracting/
# Customer Provided/Capital) are raised by Procurement/Stores.
user = frappe.session.user
if user not in ("Administrator", "Guest"):
    roles = frappe.get_all(
        "Has Role",
        filters={"parent": user, "parenttype": "User"},
        fields=["role"],
    )
    role_names = []
    for r in roles:
        role_names.append(r.role)
    is_end_user = "AIG End User" in role_names
    is_power_user = (
        ("AIG Procurement Officer" in role_names)
        or ("AIG Inventory Administrator" in role_names)
        or ("AIG Main Store Administrator" in role_names)
        or ("System Manager" in role_names)
    )
    if is_end_user and not is_power_user:
        if doc.material_request_type not in ("Purchase", "Material Issue"):
            frappe.throw(
                "AIG: End Users may raise 'Purchase' or 'Material Issue' "
                "(Model 19) requests only. Other request types belong to "
                "Procurement or Stores."
            )'''
if frappe.db.exists("Server Script", "AIG - MR End User Purchase Scope"):
    ss = frappe.get_doc("Server Script", "AIG - MR End User Purchase Scope")
    ss.script = scope_script
    ss.disabled = 0
    ss.save(ignore_permissions=True)
    log("   updated")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - MR End User Purchase Scope",
        "script_type": "DocType Event", "reference_doctype": "Material Request",
        "doctype_event": "Before Validate", "enabled": 1,
        "script": scope_script,
    }).insert(ignore_permissions=True)
    log("   created")

# --------------------------------------------- 3b. workflow masters
log("== 3b. Workflow State / Action masters")
if not frappe.db.exists("Workflow State", "Pending Head Approval"):
    frappe.get_doc({"doctype": "Workflow State",
                    "workflow_state_name": "Pending Head Approval",
                    "style": "Warning"}).insert(ignore_permissions=True)
    log("   Workflow State created: Pending Head Approval")
else:
    log("   Workflow State exists: Pending Head Approval")
for action, style in [("Submit Purchase Request", None), ("Approve & Assign", None)]:
    if not frappe.db.exists("Workflow Action Master", action):
        d = {"doctype": "Workflow Action Master",
             "workflow_action_name": action}
        if style:
            d["style"] = style
        frappe.get_doc(d).insert(ignore_permissions=True)
        log("   Workflow Action Master created:", action)
    else:
        log("   Workflow Action Master exists:", action)

# --------------------------------------------------------- 4. workflow
log("== 4. workflow: add head-first end-user purchase route")
w = frappe.get_doc("Workflow", "AIG Stock Request Approval")

states = {s.state for s in w.states}
if "Pending Head Approval" not in states:
    w.append("states", {"state": "Pending Head Approval", "doc_status": 1,
                        "allow_edit": "AIG Enterprise Head"})
    log("   state added: Pending Head Approval (doc_status=1, edit=Enterprise Head)")

want = [
    {"state": "Draft", "action": "Submit Purchase Request",
     "next_state": "Pending Head Approval", "allowed": "AIG End User",
     "condition": 'doc.material_request_type == "Purchase"'},
    {"state": "Pending Head Approval", "action": "Approve",
     "next_state": "Pending Store Review", "allowed": "AIG Enterprise Head"},
    {"state": "Pending Head Approval", "action": "Reject",
     "next_state": "Rejected", "allowed": "AIG Enterprise Head"},
    {"state": "Pending Store Review", "action": "Approve & Assign",
     "next_state": "Approved", "allowed": "AIG Main Store Administrator",
     "condition": 'doc.aig_assigned_procurement_officer'},
    {"state": "Pending Store Review", "action": "Approve",
     "next_state": "Approved", "allowed": "AIG Main Store Administrator"},
]
have = {(t.state, t.action) for t in w.transitions}
for row in want:
    if (row["state"], row["action"]) not in have:
        w.append("transitions", row)
        log("   transition added:", row["state"], "--", row["action"], "-->",
            row["next_state"])
    else:
        log("   transition exists:", row["state"], "--", row["action"])

# Move the new end-user entries to the TOP of the list: the store-Approve
# condition must be evaluated before the original condition-less Approve.
enduser_actions = {"Submit Purchase Request", "Approve & Assign"}
keep = [t for t in w.transitions if t.action not in enduser_actions]
newt = [t for t in w.transitions if t.action in enduser_actions]
w.transitions = []
for t in newt + keep:
    w.append("transitions", {
        "state": t.state, "action": t.action, "next_state": t.next_state,
        "allowed": t.allowed, "condition": t.condition,
    })
w.save(ignore_permissions=True)
log("   saved; order:", [(t.state, t.action) for t in w.transitions][:6])

# ------------------------------------------- 5. store admin write on MR
log("== 5. Custom DocPerm: Main Store Administrator write on MR")
perm = frappe.db.get_value("Custom DocPerm",
                           {"parent": "Material Request",
                            "role": "AIG Main Store Administrator"}, "name")
if perm:
    p = frappe.get_doc("Custom DocPerm", perm)
    p.write = 1
    p.submit = 1
    p.save(ignore_permissions=True)
    log("   updated: write=1 submit=1")
else:
    frappe.get_doc({
        "doctype": "Custom DocPerm", "parent": "Material Request",
        "parenttype": "DocType", "parentfield": "permissions",
        "role": "AIG Main Store Administrator",
        "read": 1, "write": 1, "create": 0, "submit": 1, "cancel": 0,
    }).insert(ignore_permissions=True)
    log("   created: read+write+submit")

frappe.clear_cache()
log("DONE 175")
