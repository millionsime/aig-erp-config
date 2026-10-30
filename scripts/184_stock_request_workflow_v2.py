# 184_stock_request_workflow_v2.py
#
# Re-routes the employee material (stock) request workflow on "AIG Stock Request
# Approval" (Material Request, type Purchase):
#
#   1. End User submits Material Request            (Draft)
#   2. Plan & Budget Office approves budget         (Pending Budget Approval)
#   3a. <= 50,000 ETB   -> Enterprise Head approves (Pending Head Approval)
#   3b. 50k..750k ETB   -> CEO approves             (Pending CEO Approval)
#   3c. > 750,000 ETB   -> Corporate approves       (Pending Corporate Approval)
#   3d. CEO's own request -> Corporate approves (CEO can never approve himself)
#   4. Record Office prints 1 copy, seals it, takes it, clicks
#      "Confirm Printed & Sealed"                   (Pending Print & Seal)
#   5. Procurement & Property Administration Director (or Main Store Admin)
#      assigns purchaser and clicks "Approve & Assign"  (Pending Store Review)
#
# Thresholds: T_HEAD / T_CORP below. The 750,000 matches the existing
# AIG Procurement Approval (Purchase Order) committee threshold on purpose.
#
# Idempotent: safe to re-run. Run with:
#   bench --site <site> console < 184_stock_request_workflow_v2.py

import frappe

WF = "AIG Stock Request Approval"
CEO_USER = "ceo@aig.local"
T_HEAD = 50000
T_CORP = 750000

# ---- 0. roles ---------------------------------------------------------------
def ensure_role(name):
    if not frappe.db.exists("Role", name):
        frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
            ignore_permissions=True
        )
        print("role created:", name)
    else:
        print("role ok:", name)

for r in ["AIG Plan and Budget", "AIG Record Office", "AIG Procurement Director"]:
    ensure_role(r)

# ---- 1. doc perms so the new roles can open Material Requests ---------------
def ensure_docperm(doctype, role):
    if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
        print("docperm ok:", doctype, role)
        return
    frappe.get_doc(
        {
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "parenttype": "DocType",
            "parentfield": "permissions",
            "role": role,
            "read": 1,
            "write": 1,
            "create": 0,
            "submit": 0,
            "cancel": 0,
            "delete": 0,
            "amend": 0,
            "report": 1,
            "print": 1,
            "email": 1,
            "share": 0,
        }
    ).insert(ignore_permissions=True)
    print("docperm added:", doctype, role)

for role in ["AIG Plan and Budget", "AIG Record Office", "AIG Procurement Director"]:
    ensure_docperm("Material Request", role)

# ---- 1b. workflow state + action master records (must exist before save) ----
def ensure_master(doctype, fieldname, value):
    if frappe.db.exists(doctype, value):
        print("master ok:", value)
        return
    frappe.get_doc({"doctype": doctype, fieldname: value}).insert(ignore_permissions=True)
    print("master created:", doctype, value)

for s in ["Pending Budget Approval", "Pending Print & Seal"]:
    ensure_master("Workflow State", "workflow_state_name", s)
for a in ["Approve Budget", "Confirm Printed & Sealed"]:
    ensure_master("Workflow Action Master", "workflow_action_name", a)

# ---- 2. workflow doc --------------------------------------------------------
wf = frappe.get_doc("Workflow", WF)

tables = {f.fieldname: f.options for f in frappe.get_meta("Workflow").fields if f.fieldtype == "Table"}
SF = [k for k, v in tables.items() if v == "Workflow Document State"][0]
TF = [k for k, v in tables.items() if v == "Workflow Transition"][0]
states = getattr(wf, SF)
transitions = getattr(wf, TF)
print("states field:", SF, "| transitions field:", TF)

def upsert_state(state, doc_status, allow_edit):
    for s in states:
        if s.state == state:
            s.doc_status = doc_status
            s.allow_edit = allow_edit
            print("state ok:", state)
            return
    wf.append(SF, {"state": state, "doc_status": doc_status, "allow_edit": allow_edit})
    print("state added:", state)

def set_transition(state, action, allowed, next_state, condition="__KEEP__", allow_self=1):
    target_cond = None if condition == "__KEEP__" else condition
    for t in transitions:
        same_row = (
            t.state == state
            and t.action == action
            and t.allowed == allowed
            and (t.condition or None) == target_cond
        )
        if same_row:
            t.next_state = next_state
            t.allow_self_approval = allow_self
            print("transition ok:", state, "|", action, "|", allowed, "->", next_state)
            return
    row = {
        "state": state,
        "action": action,
        "next_state": next_state,
        "allowed": allowed,
        "allow_self_approval": allow_self,
        "condition": target_cond,
    }
    wf.append(TF, row)
    print("transition added:", state, "|", action, "|", allowed, "->", next_state)

# ---- 3. new states ----------------------------------------------------------
upsert_state("Pending Budget Approval", "1", "AIG Plan and Budget")
upsert_state("Pending Print & Seal", "1", "AIG Record Office")
# approver tiers referenced by the budget routing (must be rows in THIS workflow)
upsert_state("Pending CEO Approval", "1", "AIG CEO")
upsert_state("Pending Corporate Approval", "1", "AIG Corporate")
# step 5 owner: the Procurement & Property Administration Director edits the
# request in "Pending Store Review" to fill aig_assigned_procurement_officer.
# (Legacy main-store users are ALSO granted AIG Procurement Director by 183,
# so existing users keep full function.)
upsert_state("Pending Store Review", "1", "AIG Procurement Director")

# ---- 4. step 1: end user submits -> BUDGET first (was -> Head) ---------------
set_transition(
    "Draft", "Submit Purchase Request", "AIG End User",
    next_state="Pending Budget Approval",
)

# ---- 5. step 2+3: budget office approves, amount decides the route ----------
NOT_CEO = ' and doc.owner != "%s"' % CEO_USER
set_transition(
    "Pending Budget Approval", "Approve Budget", "AIG Plan and Budget",
    next_state="Pending Head Approval",
    condition="(doc.aig_estimated_total or 0) <= %d%s" % (T_HEAD, NOT_CEO),
)
set_transition(
    "Pending Budget Approval", "Approve Budget", "AIG Plan and Budget",
    next_state="Pending CEO Approval",
    condition="(doc.aig_estimated_total or 0) > %d and (doc.aig_estimated_total or 0) <= %d%s"
    % (T_HEAD, T_CORP, NOT_CEO),
)
set_transition(
    "Pending Budget Approval", "Approve Budget", "AIG Plan and Budget",
    next_state="Pending Corporate Approval",
    condition="(doc.aig_estimated_total or 0) > %d%s" % (T_CORP, NOT_CEO),
)
# CEO's own requests: nobody below the CEO may approve them -> Corporate always
set_transition(
    "Pending Budget Approval", "Approve Budget", "AIG Plan and Budget",
    next_state="Pending Corporate Approval",
    condition='doc.owner == "%s"' % CEO_USER,
)
set_transition(
    "Pending Budget Approval", "Reject", "AIG Plan and Budget",
    next_state="Rejected", condition="__KEEP__",
)

# ---- 6. step 3 approvers hand over to RECORD OFFICE (was -> Store/Approved) --
set_transition("Pending Head Approval", "Approve", "AIG Enterprise Head",
               next_state="Pending Print & Seal")
set_transition("Pending CEO Approval", "Approve", "AIG CEO",
               next_state="Pending Print & Seal")
set_transition("Pending Corporate Approval", "Approve", "AIG Corporate",
               next_state="Pending Print & Seal")

# ---- 7. step 4: record office prints, seals, carries the copy, clicks done ---
set_transition("Pending Print & Seal", "Confirm Printed & Sealed", "AIG Record Office",
               next_state="Pending Store Review")
set_transition("Pending Print & Seal", "Reject", "AIG Record Office",
               next_state="Rejected")

# ---- 8. step 5: procurement director OR main store admin assigns purchaser ---
set_transition("Pending Store Review", "Approve & Assign", "AIG Main Store Administrator",
               next_state="Approved",
               condition='doc.material_request_type == "Purchase" and doc.aig_assigned_procurement_officer')
set_transition("Pending Store Review", "Approve & Assign", "AIG Procurement Director",
               next_state="Approved",
               condition='doc.material_request_type == "Purchase" and doc.aig_assigned_procurement_officer')

wf.save(ignore_permissions=True)
frappe.db.commit()
frappe.clear_cache()

print("")
print("=== FINAL: states ===")
for s in states:
    print("  %-38s doc_status=%s edit=%s" % (s.state, s.doc_status, s.allow_edit))
print("=== FINAL: transitions ===")
for t in transitions:
    print("  %-30s %-26s %-32s -> %-32s [%s] %s" % (
        t.state, t.action, t.allowed, t.next_state,
        t.allow_self_approval, t.condition or ""))
print("184 DONE")
