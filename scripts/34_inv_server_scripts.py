# AIG config - step 34: INVENTORY Server Scripts (RestrictedPython, config layer).
# Enforces business rules WITHOUT touching core code:
#   MR  - request defaults; self-approval block; honest budget-check recording
#   SE  - movement defaults (main-store flag + enterprise cost centers);
#         receiving inspection gate (Quality Form); raw-submit guard;
#         issue-vs-approved-request validation
# All scripts are RestrictedPython-safe (no underscore-prefixed names). Idempotent:
# re-running refreshes the script body. NO core edits.
import frappe
import traceback

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def set_script(name, reference_doctype, doctype_event, script):
    if frappe.db.exists("Server Script", name):
        ss = frappe.get_doc("Server Script", name)
        if ss.script != script or ss.disabled or ss.doctype_event != doctype_event:
            ss.script = script
            ss.disabled = 0
            ss.doctype_event = doctype_event
            ss.reference_doctype = reference_doctype
            ss.script_type = "DocType Event"
            ss.flags.ignore_permissions = True
            ss.save(ignore_permissions=True)
            log("UPDATE", f"Server Script {name}")
        else:
            log("EXISTS", f"Server Script {name}")
        return name
    doc = frappe.get_doc({
        "doctype": "Server Script", "name": name, "script_type": "DocType Event",
        "reference_doctype": reference_doctype, "doctype_event": doctype_event,
        "script": script, "disabled": 0,
    })
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"Server Script {name}")
    except Exception:
        print(f"!! FAILED {name}")
        print(traceback.format_exc())
    return name


# ============================================ MR: request defaults (Before Insert)
MR_DEFAULTS = """# AIG - default the requester and enterprise cost center on a new Stock Request.
if not doc.get("aig_requested_by"):
    doc.aig_requested_by = frappe.session.user
if not doc.get("aig_cost_center"):
    cc = frappe.db.get_value("User Permission",
                             {"user": frappe.session.user, "allow": "Cost Center"},
                             "for_value")
    if not cc:
        cc = frappe.db.get_value("Company", doc.company, "cost_center")
    if cc:
        doc.aig_cost_center = cc
"""
set_script("AIG - MR Request Defaults", "Material Request", "Before Insert", MR_DEFAULTS)

# ========================= MR: self-approval block + budget-check (submitted save)
MR_GUARD = """# AIG separation-of-duties + honest budget recording on a Stock Request.
# Fires when a submitted request is moved by a workflow action.
requester = doc.get("aig_requested_by") or doc.owner
approval_states = ["Pending Enterprise Approval", "Approved"]
if doc.workflow_state in approval_states and frappe.session.user == requester:
    frappe.throw("AIG separation of duties: a requester cannot approve their own stock request.")

if doc.workflow_state == "Pending Enterprise Approval":
    note = doc.get("aig_budget_note") or ""
    if not doc.get("aig_budget_checked") and not str(note).strip():
        frappe.throw("Store review must record the budget check: tick 'Budget Checked' "
                     "or state in 'Budget Check Note' that budget data was unavailable. "
                     "Do not fabricate a budget validation.")
"""
set_script("AIG - MR Approval Guard", "Material Request",
           "Before Save (Submitted Document)", MR_GUARD)

# ===================== SE: movement defaults (main-store flag + cost centers)
SE_DEFAULTS = """# AIG - capture enterprise dimensions and flag Main Store final approval.
recv_wh = doc.to_warehouse
src_wh = doc.from_warehouse
if not recv_wh:
    for it in (doc.items or []):
        if it.t_warehouse:
            recv_wh = it.t_warehouse
            break
if not src_wh:
    for it in (doc.items or []):
        if it.s_warehouse:
            src_wh = it.s_warehouse
            break

is_main = 0
dst_cc = None
src_cc = None
if recv_wh:
    dst_cc = frappe.db.get_value("Warehouse", recv_wh, "aig_cost_center")
    is_main = frappe.db.get_value("Warehouse", recv_wh, "aig_is_main_store") or 0
if src_wh:
    src_cc = frappe.db.get_value("Warehouse", src_wh, "aig_cost_center")

doc.aig_needs_main_approval = 1 if (doc.purpose == "Material Receipt" and is_main) else 0
if src_cc and not doc.get("aig_source_cost_center"):
    doc.aig_source_cost_center = src_cc
if dst_cc and not doc.get("aig_dest_cost_center"):
    doc.aig_dest_cost_center = dst_cc
if not doc.get("aig_cost_center"):
    fallback = dst_cc or src_cc
    if not fallback:
        fallback = frappe.db.get_value("User Permission",
                                       {"user": frappe.session.user, "allow": "Cost Center"},
                                       "for_value")
    if fallback:
        doc.aig_cost_center = fallback
"""
set_script("AIG - SE Movement Defaults", "Stock Entry", "Before Save", SE_DEFAULTS)

# ===================== SE: receiving inspection gate (Quality Form required)
SE_INSPECTION_GATE = """# AIG receiving: a submitted Quality Inspection (Quality Form) for this receipt
# must exist before the General Store Keeper approval step.
if doc.workflow_state == "Pending GSK Approval":
    qi = frappe.db.get_all("Quality Inspection",
                           filters={"reference_type": "Stock Entry",
                                    "reference_name": doc.name, "docstatus": 1},
                           fields=["name"])
    if not qi:
        frappe.throw("AIG receiving: record and submit a Quality Inspection (Quality Form) "
                     "for this receipt before requesting General Store Keeper approval.")
"""
set_script("AIG - SE Receiving Inspection Gate", "Stock Entry", "Before Save", SE_INSPECTION_GATE)

# ===================== SE: raw-submit guard (post stock only via Posted state)
SE_SUBMIT_GUARD = """# AIG guard: stock may only be posted by reaching the 'Posted' workflow state.
if doc.workflow_state != "Posted":
    frappe.throw("AIG guard: a Stock Entry can only be submitted (stock posted) by reaching "
                 "the 'Posted' workflow state. Raw submit is blocked so receiving approvals "
                 "cannot be bypassed.")
"""
set_script("AIG - SE Guard Raw Submit", "Stock Entry", "Before Submit", SE_SUBMIT_GUARD)

# ===================== SE: issue validation (Material Issue vs approved request)
SE_ISSUE_CHECK = """# AIG issue control: a Material Issue must reference an APPROVED Stock Request
# (Model 19) and may not issue more than the approved remaining quantity.
if doc.purpose == "Material Issue":
    mr = doc.get("aig_material_request")
    if not mr:
        for it in (doc.items or []):
            if it.material_request:
                mr = it.material_request
                break
    if not mr:
        frappe.throw("AIG issue: link the approved Stock Request (Model 19) in "
                     "'Against Stock Request' before posting an issue.")
    mr_doc = frappe.get_doc("Material Request", mr)
    if mr_doc.workflow_state != "Approved":
        frappe.throw("AIG issue: Stock Request " + str(mr) + " is not Approved (state: "
                     + str(mr_doc.workflow_state) + ").")

    requested = {}
    for r in (mr_doc.items or []):
        requested[r.item_code] = (requested.get(r.item_code) or 0) + (r.qty or 0)

    rows = frappe.db.sql(
        "select sed.item_code as item_code, sum(sed.qty) as qty "
        "from `tabStock Entry Detail` sed "
        "join `tabStock Entry` se on se.name = sed.parent "
        "where se.aig_material_request = %s and se.docstatus = 1 "
        "group by sed.item_code", (mr,), as_dict=True)
    already = {}
    for row in (rows or []):
        already[row.item_code] = row.qty or 0

    this_issue = {}
    for it in (doc.items or []):
        this_issue[it.item_code] = (this_issue.get(it.item_code) or 0) + (it.qty or 0)

    for code in this_issue:
        allowed = requested.get(code)
        if allowed is None:
            frappe.throw("AIG issue: item " + str(code) + " is not on approved Stock Request "
                         + str(mr) + ".")
        total = (already.get(code) or 0) + this_issue[code]
        if total > allowed:
            frappe.throw("AIG issue: item " + str(code) + " would total " + str(total)
                         + " against an approved quantity of " + str(allowed)
                         + ". Reduce the issue or amend the request.")
"""
set_script("AIG - SE Issue Validation", "Stock Entry", "Before Submit", SE_ISSUE_CHECK)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP34_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
