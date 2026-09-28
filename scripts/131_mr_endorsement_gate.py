# 131_mr_endorsement_gate.py -- Refined brief Section 3.1: Enterprise Head
# Endorsement gate on Material Request for Bulky-tier procurement needs.
#   - New custom field aig_estimated_total (Currency, ETB) on Material Request
#     (Section 5 open item #2 resolved: no standard single "estimated total"
#     exists on Material Request; adding a manual field per the brief).
#   - Workflow Action Masters: "Submit for Endorsement", "Endorse".
#   - Edit "AIG Stock Request Approval" IN PLACE:
#       * CORRECT the Procurement Officer bypass transition: it previously sent
#         every non-Issue request straight to Approved; now it only applies at
#         or below ETB 750,000.
#       * ADD states "Pending Enterprise Head Endorsement" + "Endorsed" and
#         transitions Draft>Gate (cond > 750000), Endorse, Reject.
# The word "CEO" must not appear on this gate (Section 1.1) - the action is
# "Endorse", the role is AIG Enterprise Head.

import frappe

DT = "Material Request"
WF = "AIG Stock Request Approval"


def log(*a):
    print(*a, flush=True)


log("STEP 1: custom field aig_estimated_total (Currency, ETB)")
if frappe.db.exists("Custom Field", f"{DT}-aig_estimated_total"):
    log("  exists")
else:
    frappe.get_doc({
        "doctype": "Custom Field", "dt": DT,
        "fieldname": "aig_estimated_total", "fieldtype": "Currency",
        "label": "Estimated Total (ETB)",
        "description": "Estimated value of this request. Above ETB 750,000 the "
                       "request must be endorsed by the Enterprise Head before "
                       "RFQ/Tender (Bulky/Open Tender tier).",
        "insert_after": "aig_cost_center", "non_negative": 1,
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("STEP 2: workflow action masters")
for action in ["Submit for Endorsement", "Endorse"]:
    if not frappe.db.exists("Workflow Action Master", action):
        frappe.get_doc({"doctype": "Workflow Action Master",
                        "workflow_action_name": action}).insert(ignore_permissions=True)
        log(f"  created action master: {action}")
    else:
        log(f"  exists: {action}")

log("")
log("STEP 2b: workflow state masters (the workflow rows are Links to these)")
for state, typ in [("Pending Enterprise Head Endorsement", "Pending"),
                   ("Endorsed", "Success")]:
    if not frappe.db.exists("Workflow State", state):
        frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state,
                        "type": typ}).insert(ignore_permissions=True)
        log(f"  created state master: {state}")
    else:
        log(f"  exists: {state}")

log("")
log("STEP 3: edit workflow in place")
wf = frappe.get_doc("Workflow", WF)
states = {s.state for s in wf.states}

if "Pending Enterprise Head Endorsement" not in states:
    wf.append("states", {
        "state": "Pending Enterprise Head Endorsement", "idx": 2,
        "doc_status": 0, "allow_edit": "AIG Enterprise Head",
    })
    log("  state added: Pending Enterprise Head Endorsement (doc_status 0)")
else:
    log("  state exists: Pending Enterprise Head Endorsement")

if "Endorsed" not in states:
    wf.append("states", {
        "state": "Endorsed", "idx": 8,
        "doc_status": 1, "allow_edit": "AIG Procurement Officer",
    })
    log("  state added: Endorsed (doc_status 1)")
else:
    log("  state exists: Endorsed")

# corrected/new transitions: (state, action, next_state, allowed, condition)
wanted = [
    ("Draft", "Submit for Endorsement", "Pending Enterprise Head Endorsement",
     "AIG Procurement Officer",
     'doc.material_request_type != "Material Issue" and flt(doc.aig_estimated_total) > 750000'),
    ("Pending Enterprise Head Endorsement", "Endorse", "Endorsed",
     "AIG Enterprise Head", None),
    ("Pending Enterprise Head Endorsement", "Reject", "Rejected",
     "AIG Enterprise Head", None),
]

existing = {(t.state, t.action, t.next_state) for t in wf.transitions}
for st, act, nxt, allowed, cond in wanted:
    if (st, act, nxt) in existing:
        log(f"  transition exists: {st} --[{act}]--> {nxt}")
        continue
    wf.append("transitions", {"state": st, "action": act, "next_state": nxt,
                              "allowed": allowed, "condition": cond})
    log(f"  transition added: {st} --[{act}]({allowed})--> {nxt}")

# CORRECT the bypass: Procurement Officer direct-to-Approved must ONLY apply
# at or below 750000, otherwise the endorsement gate is skippable.
corrected = False
for t in wf.transitions:
    if (t.state == "Draft" and t.action == "Submit Request"
            and t.allowed == "AIG Procurement Officer"):
        new_cond = ('doc.material_request_type != "Material Issue" '
                    'and flt(doc.aig_estimated_total) <= 750000')
        if t.condition != new_cond:
            log(f"  correcting bypass condition: {t.condition!r} -> {new_cond!r}")
            t.condition = new_cond
            corrected = True
        else:
            log("  bypass condition already correct")
if corrected:
    log("  (workflow state cache will be cleared below)")

wf.flags.ignore_permissions = True
wf.save(ignore_permissions=True)
frappe.clear_cache()
log("  workflow saved + cache cleared")

log("")
log("STEP 4: verify saved workflow")
wf2 = frappe.get_doc("Workflow", WF)
for t in wf2.transitions:
    log(f"  {t.state!r} --[{t.action}]({t.allowed}; {t.condition!r})--> {t.next_state!r}")

log("")
log("STEP 5: 'CEO' wording audit on the gate (Section 1.1)")
bad = []
for s in wf2.states:
    if s.state and "CEO" in s.state:
        bad.append(f"state {s.state!r}")
for t in wf2.transitions:
    if "CEO" in (t.action or ""):
        bad.append(f"action {t.action!r}")
cf = frappe.get_doc("Custom Field", f"{DT}-aig_estimated_total")
if "CEO" in (cf.label or "") + (cf.description or ""):
    bad.append("aig_estimated_total label/description")
log(f"  audit result: {'CLEAN' if not bad else 'FAIL: ' + str(bad)}")

log("")
log("DONE 131: endorsement gate configured.")
