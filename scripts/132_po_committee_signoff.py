# 132_po_committee_signoff.py -- Refined brief Section 3.2 + 3.3:
#   A) New custom DocType "AIG Committee Signoff" (one row per committee
#      member per Purchase Order; row-owner permissions so a member can only
#      create/edit their own row).
#   B) Server scripts:
#        "AIG - CS Guard"          (Before Save on AIG Committee Signoff:
#                                   member = session.user, one row per member,
#                                   only while PO is in Pending Committee
#                                   Signoff, decision Approve/Reject).
#        "AIG - PO Committee Majority" (Before Validate on Purchase Order:
#                                   blocks the state CHANGE out of Pending
#                                   Committee Signoff with <2 Approve or
#                                   with >=2 Reject sign-offs; for the Bulky
#                                   destination also verifies the upstream
#                                   Material Request was endorsed by the
#                                   Enterprise Head).
#   C) Edit "AIG Procurement Approval" IN PLACE: rename committee stage to
#      "Pending Committee Signoff" (doc_status 0 so members can act),
#      add missing Direct-tier Finance sign-off (Section 2), keep
#      Corporate -> CEO chain intact, keep "CEO" wording only for the Group
#      CEO role (Section 1.1).
#   D) Correct "AIG - PO Cost Center Default" (same root-CC-first fallback
#      bug fixed on MR in script 120) so enterprise-scoped Procurement users
#      can still read their own POs and drive the workflow.

import frappe

PO = "Purchase Order"
WF = "AIG Procurement Approval"


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- A. DocType
log("A) custom DocType 'AIG Committee Signoff'")
if not frappe.db.exists("DocType", "AIG Committee Signoff"):
    frappe.get_doc({
        "doctype": "DocType",
        "name": "AIG Committee Signoff",
        "module": "AIG HR",
        "naming_rule": "By \"Naming Series\" field",
        "autoname": "hash",
        "istable": 0, "issingle": 0, "is_submittable": 0, "custom": 1,
        "track_changes": 1,
        "fields": [
            {"fieldname": "parent_po", "fieldtype": "Link",
             "options": "Purchase Order", "label": "Purchase Order",
             "reqd": 1, "in_list_view": 1},
            {"fieldname": "committee_member", "fieldtype": "Link",
             "options": "User", "label": "Committee Member",
             "reqd": 1, "in_list_view": 1, "read_only": 1},
            {"fieldname": "member_role", "fieldtype": "Link",
             "options": "Role", "label": "Role", "read_only": 1,
             "default": "AIG Purchase Committee", "hidden": 1},
            {"fieldname": "decision", "fieldtype": "Select",
             "label": "Decision", "options": "Approve\nReject",
             "reqd": 1, "in_list_view": 1},
            {"fieldname": "decision_date", "fieldtype": "Date",
             "label": "Decision Date", "read_only": 1, "default": "Today",
             "in_list_view": 1},
            {"fieldname": "comments", "fieldtype": "Small Text",
             "label": "Comments"},
        ],
        "permissions": [
            # each member: full control over OWN rows only
            {"role": "AIG Purchase Committee", "read": 1, "write": 1,
             "create": 1, "delete": 1, "if_owner": 1},
            # auditors/admin can see all rows
            {"role": "AIG Inventory Administrator", "read": 1},
            {"role": "AIG Internal Auditor", "read": 1},
            {"role": "System Manager", "read": 1, "write": 1, "create": 1},
        ],
    }).insert(ignore_permissions=True)
    log("  created doctype")
else:
    log("  doctype already exists (left as-is)")

# ----------------------------------------------------------------- B. Scripts
log("")
log("B) server scripts")

CS_GUARD = """# AIG - CS Guard (AIG Committee Signoff, Before Save). Integrity rules for
# the 2-of-3 Purchase Committee majority:
#   - committee_member is ALWAYS the signed-in user (nobody signs for anyone
#     else; Administrator may pre-seed a row by setting committee_member).
#   - exactly one sign-off row per member per Purchase Order (edit your row
#     instead of adding another).
#   - decisions are only recorded while the PO is in 'Pending Committee
#     Signoff' (doc_status 0 stage).
#   - decision is Approve or Reject; decision_date defaults to today.
member = frappe.session.user
if member == "Administrator" and doc.get("committee_member"):
    member = doc.committee_member
doc.committee_member = member
if doc.decision not in ("Approve", "Reject"):
    frappe.throw("AIG Committee Signoff: decision must be Approve or Reject.")
po_state = frappe.db.get_value("Purchase Order", doc.parent_po, "workflow_state")
if po_state != "Pending Committee Signoff":
    frappe.throw("AIG Committee Signoff: sign-offs are only recorded while the "
                 "Purchase Order is in 'Pending Committee Signoff'.")
dup = frappe.get_all("AIG Committee Signoff",
                     filters={"parent_po": doc.parent_po,
                              "committee_member": member},
                     pluck="name")
for d in dup:
    if d != doc.name:
        frappe.throw("You have already recorded a decision on this Purchase "
                     "Order. Edit your existing sign-off row instead.")
if not doc.decision_date:
    doc.decision_date = frappe.utils.nowdate()
"""

if frappe.db.exists("Server Script", "AIG - CS Guard"):
    row = frappe.get_doc("Server Script", "AIG - CS Guard")
    row.script = CS_GUARD
    row.disabled = 0
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  AIG - CS Guard updated")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - CS Guard",
        "script_type": "DocType Event", "reference_doctype": "AIG Committee Signoff",
        "doctype_event": "Before Save", "disabled": 0, "script": CS_GUARD,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  AIG - CS Guard created")

MAJORITY = """# AIG - PO Committee Majority (Purchase Order, Before Validate).
# Section 3.2 of the refined brief: 2 of 3 named committee members must have
# 'Approve' sign-off rows before the PO may LEAVE 'Pending Committee Signoff',
# and 2 'Reject' rows must force the Rejected outcome (the matching workflow
# actions become functional exactly at that count - the script blocks the
# transition otherwise). Also enforces the Bulky/Open-Tender precondition:
# the upstream Material Request must be Enterprise-Head-endorsed (Section 3.1).
# Only fires on a STATE CHANGE out of the sign-off stage; plain edits inside
# the stage (fixing items, adding rows) stay possible.
prev = getattr(doc, "_doc_before_save", None)
prev_state = prev.get("workflow_state") if prev else None
state = doc.get("workflow_state")
if prev_state == "Pending Committee Signoff" and \
        state != "Pending Committee Signoff":
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
            frappe.throw("AIG 2-of-3 rule: a committee rejection needs at least "
                         "2 'Reject' sign-offs; only " + str(len(rejects)) +
                         " recorded so far.")
    else:
        if len(rejects) >= 2:
            frappe.throw("AIG 2-of-3 rule: 2 'Reject' sign-offs are recorded - "
                         "this Purchase Order must be Rejected by the committee.")
        if len(approvals) < 2:
            frappe.throw("AIG 2-of-3 rule: " + str(2 - len(approvals)) +
                         " more committee approval(s) needed - only " +
                         str(len(approvals)) + " of 3 'Approve' sign-offs are "
                         "recorded.")
        if flt(doc.grand_total) > 750000:
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
"""

if frappe.db.exists("Server Script", "AIG - PO Committee Majority"):
    row = frappe.get_doc("Server Script", "AIG - PO Committee Majority")
    row.script = MAJORITY
    row.disabled = 0
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  AIG - PO Committee Majority updated")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - PO Committee Majority",
        "script_type": "DocType Event", "reference_doctype": PO,
        "doctype_event": "Before Validate", "disabled": 0, "script": MAJORITY,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  AIG - PO Committee Majority created")

PO_CC = """# AIG: default the mandatory AIG Cost Center on Purchase Order.
# Order: first item cost_center -> creating user's first UNSCOPED Cost Center
# user permission (root CC / Head Office excluded: enterprise users cannot
# read documents carrying them) -> company default.
if not doc.get("aig_cost_center"):
    cc = None
    for item in (doc.items or []):
        if item.get("cost_center"):
            cc = item.get("cost_center")
            break
    if not cc:
        rows = frappe.get_all("User Permission",
                              filters={"user": frappe.session.user,
                                       "allow": "Cost Center"},
                              fields=["for_value", "applicable_for"])
        for r in rows:
            if r.for_value in ("Adama Investment Group - AIG",
                               "Head Office - AIG"):
                continue
            if r.applicable_for and r.applicable_for != "Cost Center":
                continue
            cc = r.for_value
            break
    if not cc:
        cc = frappe.db.get_value("Company", doc.company, "cost_center")
    if cc in ("Adama Investment Group - AIG", "Head Office - AIG"):
        cc = None
    if cc:
        doc.set("aig_cost_center", cc)
for item in (doc.items or []):
    if not item.get("cost_center") and doc.get("aig_cost_center"):
        item.cost_center = doc.get("aig_cost_center")
"""

row = frappe.get_doc("Server Script", "AIG - PO Cost Center Default")
row.script = PO_CC
row.flags.ignore_permissions = True
row.save(ignore_permissions=True)
log("  AIG - PO Cost Center Default corrected (root/HO fallback removed)")

# --------------------------------------------------------------- C. Workflow
log("")
log("C) workflow 'AIG Procurement Approval' edited in place")

for state, typ in [("Pending Committee Signoff", "Pending"),
                   ("Pending Finance Signoff", "Pending")]:
    if not frappe.db.exists("Workflow State", state):
        frappe.get_doc({"doctype": "Workflow State",
                        "workflow_state_name": state, "type": typ}
                       ).insert(ignore_permissions=True)
        log(f"  state master created: {state}")

for action in ["Finalize Committee Decision", "Forward to Tender Committee",
               "Finance Sign-off"]:
    if not frappe.db.exists("Workflow Action Master", action):
        frappe.get_doc({"doctype": "Workflow Action Master",
                        "workflow_action_name": action}
                       ).insert(ignore_permissions=True)
        log(f"  action master created: {action}")

wf = frappe.get_doc("Workflow", WF)

desired_states = [
    ("Draft", 0, "AIG Procurement Officer"),
    ("Pending Committee Signoff", 0, "AIG Procurement Officer"),
    ("Pending Enterprise Head Approval", 1, "AIG Enterprise Head"),
    ("Pending Corporate Approval", 1, "AIG Corporate"),
    ("Pending CEO Approval", 1, "AIG CEO"),
    ("Pending Finance Signoff", 0, "AIG Finance"),
    ("Approved", 1, "System Manager"),
    ("Rejected", 2, "System Manager"),
]
wf.states = []
for name, ds, editor in desired_states:
    wf.append("states", {"state": name, "doc_status": ds, "allow_edit": editor})

desired_transitions = [
    ("Draft", "Submit for Direct Purchase", "Pending Finance Signoff",
     "AIG Procurement Officer", "flt(doc.grand_total) < 20000"),
    ("Draft", "Submit for Committee Review", "Pending Committee Signoff",
     "AIG Procurement Officer", "flt(doc.grand_total) >= 20000"),
    ("Pending Committee Signoff", "Finalize Committee Decision",
     "Pending Enterprise Head Approval", "AIG Purchase Committee",
     "flt(doc.grand_total) <= 750000"),
    ("Pending Committee Signoff", "Forward to Tender Committee",
     "Pending Corporate Approval", "AIG Purchase Committee",
     "flt(doc.grand_total) > 750000"),
    ("Pending Committee Signoff", "Reject", "Rejected",
     "AIG Purchase Committee", None),
    ("Pending Enterprise Head Approval", "Approve", "Approved",
     "AIG Enterprise Head", None),
    ("Pending Enterprise Head Approval", "Reject", "Rejected",
     "AIG Enterprise Head", None),
    ("Pending Corporate Approval", "Approve", "Pending CEO Approval",
     "AIG Corporate", None),
    ("Pending Corporate Approval", "Reject", "Rejected", "AIG Corporate", None),
    ("Pending CEO Approval", "Approve", "Approved", "AIG CEO", None),
    ("Pending CEO Approval", "Reject", "Rejected", "AIG CEO", None),
    ("Pending Finance Signoff", "Finance Sign-off", "Approved",
     "AIG Finance", None),
    ("Pending Finance Signoff", "Reject", "Rejected", "AIG Finance", None),
]
wf.transitions = []
for st, act, nxt, allowed, cond in desired_transitions:
    wf.append("transitions", {"state": st, "action": act, "next_state": nxt,
                              "allowed": allowed, "condition": cond})

wf.flags.ignore_permissions = True
wf.save(ignore_permissions=True)
frappe.clear_cache()
log("  states + transitions rewritten (see verification below)")

wf2 = frappe.get_doc("Workflow", WF)
for s in wf2.states:
    log(f"  state: {s.state!r} doc_status={s.doc_status} edit={s.allow_edit}")
for t in wf2.transitions:
    log(f"  {t.state!r} --[{t.action}]({t.allowed}; {t.condition!r})--> {t.next_state!r}")

log("")
log("D) 'CEO' wording audit on the PO chain (Section 1.1)")
bad = []
for t in wf2.transitions:
    if t.allowed == "AIG Enterprise Head" and "CEO" in (t.action or ""):
        bad.append(t.action)
log(f"  {'CLEAN' if not bad else 'FAIL: ' + str(bad)} - Enterprise Head actions: "
    f"{[t.action for t in wf2.transitions if t.allowed == 'AIG Enterprise Head']}")

log("")
log("DONE 132")
