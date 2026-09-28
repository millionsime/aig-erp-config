# AIG config - step 33: INVENTORY transaction fields + workflows (config layer).
# Adds Custom Fields to Material Request / Stock Entry / Stock Reconciliation and
# builds two Workflows:
#   * "AIG Stock Request Approval"  (Material Request)  - Model 19 request flow
#   * "AIG Store Receiving"         (Stock Entry)        - receiving + movement
# KEY DESIGN (v16): stock posts only when a Stock Entry is SUBMITTED. All receiving
# approval states are docstatus 0 (Draft); only "Posted" is docstatus 1, so rejected
# /in-approval receipts never enter available stock. A Before-Submit guard (step 34)
# blocks any raw submit that bypasses the workflow. NO core edits.
import frappe
import traceback

COMPANY = "Adama Investment Group"
ABBR = "AIG"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def insert_doc(values, label):
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


def get_or_create(dt, filters, values, label):
    name = frappe.db.get_value(dt, filters)
    if name:
        log("EXISTS", f"{label}: {name}")
        return name
    merged = {"doctype": dt}
    merged.update(values)
    return insert_doc(merged, label)


def cf(dt, fieldname, values, label):
    if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
        log("EXISTS", f"Custom Field {dt}.{fieldname}")
        return fieldname
    merged = {"doctype": "Custom Field", "dt": dt, "fieldname": fieldname}
    merged.update(values)
    return insert_doc(merged, label)


# ============================================================ Custom Fields
# ---- Material Request (Model 19 stock request) ----
cf("Material Request", "aig_cost_center", {
    "label": "AIG Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "reqd": 1, "insert_after": "company", "in_list_view": 1, "in_standard_filter": 1,
}, "Custom Field MR.aig_cost_center")
cf("Material Request", "aig_requested_by", {
    "label": "Requested By", "fieldtype": "Link", "options": "User", "insert_after": "aig_cost_center",
}, "Custom Field MR.aig_requested_by")
cf("Material Request", "aig_purpose_note", {
    "label": "Purpose", "fieldtype": "Small Text", "insert_after": "aig_requested_by",
}, "Custom Field MR.aig_purpose_note")
cf("Material Request", "aig_destination_warehouse", {
    "label": "Destination Store", "fieldtype": "Link", "options": "Warehouse",
    "insert_after": "aig_purpose_note",
}, "Custom Field MR.aig_destination_warehouse")
cf("Material Request", "aig_budget_checked", {
    "label": "Budget Checked", "fieldtype": "Check", "insert_after": "aig_destination_warehouse",
}, "Custom Field MR.aig_budget_checked")
cf("Material Request", "aig_budget_note", {
    "label": "Budget Check Note", "fieldtype": "Small Text", "insert_after": "aig_budget_checked",
    "description": "If budget data was unavailable, state that here. Do not fabricate a check.",
}, "Custom Field MR.aig_budget_note")
cf("Material Request", "aig_issue_reference", {
    "label": "Issue Reference (Stock Entry)", "fieldtype": "Link", "options": "Stock Entry",
    "insert_after": "aig_budget_note", "read_only": 1,
}, "Custom Field MR.aig_issue_reference")
cf("Material Request", "aig_received_by", {
    "label": "Received By (End User)", "fieldtype": "Link", "options": "User",
    "insert_after": "aig_issue_reference",
}, "Custom Field MR.aig_received_by")
cf("Material Request", "aig_received_on", {
    "label": "Received On", "fieldtype": "Datetime", "insert_after": "aig_received_by",
}, "Custom Field MR.aig_received_on")
cf("Material Request", "aig_receipt_confirmed", {
    "label": "Receipt Confirmed", "fieldtype": "Check", "insert_after": "aig_received_on",
}, "Custom Field MR.aig_receipt_confirmed")
cf("Material Request", "aig_receipt_note", {
    "label": "Receipt Confirmation Note", "fieldtype": "Small Text", "insert_after": "aig_receipt_confirmed",
}, "Custom Field MR.aig_receipt_note")

# ---- Stock Entry (receiving / issue / transfer) ----
cf("Stock Entry", "aig_cost_center", {
    "label": "AIG Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "company", "in_list_view": 1, "in_standard_filter": 1,
}, "Custom Field SE.aig_cost_center")
cf("Stock Entry", "aig_source_cost_center", {
    "label": "Source Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "aig_cost_center",
}, "Custom Field SE.aig_source_cost_center")
cf("Stock Entry", "aig_dest_cost_center", {
    "label": "Destination Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "aig_source_cost_center",
}, "Custom Field SE.aig_dest_cost_center")
cf("Stock Entry", "aig_material_request", {
    "label": "Against Stock Request (Model 19)", "fieldtype": "Link", "options": "Material Request",
    "insert_after": "aig_dest_cost_center",
}, "Custom Field SE.aig_material_request")
cf("Stock Entry", "aig_source_ref", {
    "label": "Source / Reference Document", "fieldtype": "Data", "insert_after": "aig_material_request",
    "description": "Purchase order, transfer or delivery note reference for the receipt.",
}, "Custom Field SE.aig_source_ref")
cf("Stock Entry", "aig_needs_main_approval", {
    "label": "Needs Main Store Final Approval", "fieldtype": "Check",
    "insert_after": "aig_source_ref", "read_only": 1,
}, "Custom Field SE.aig_needs_main_approval")
cf("Stock Entry", "aig_inspected_by", {
    "label": "Inspected By", "fieldtype": "Link", "options": "User", "insert_after": "aig_needs_main_approval",
}, "Custom Field SE.aig_inspected_by")
cf("Stock Entry", "aig_inspection_notes", {
    "label": "Inspection Notes", "fieldtype": "Small Text", "insert_after": "aig_inspected_by",
}, "Custom Field SE.aig_inspection_notes")
cf("Stock Entry", "aig_issued_to", {
    "label": "Issued To (Recipient)", "fieldtype": "Link", "options": "User",
    "insert_after": "aig_inspection_notes",
}, "Custom Field SE.aig_issued_to")

# ---- Stock Reconciliation (counts / adjustments) ----
cf("Stock Reconciliation", "aig_cost_center", {
    "label": "AIG Enterprise (Cost Center)", "fieldtype": "Link", "options": "Cost Center",
    "insert_after": "company", "in_standard_filter": 1,
}, "Custom Field SR.aig_cost_center")
cf("Stock Reconciliation", "aig_reason_code", {
    "label": "Reason Code", "fieldtype": "Select",
    "options": "\nStock Count Variance\nDamaged\nExpired\nObsolete\nQuarantined\nCorrection\nOpening Balance\nOther",
    "reqd": 1, "insert_after": "aig_cost_center", "in_list_view": 1,
}, "Custom Field SR.aig_reason_code")
cf("Stock Reconciliation", "aig_reason_note", {
    "label": "Reason / Supporting Notes", "fieldtype": "Small Text", "reqd": 1,
    "insert_after": "aig_reason_code",
}, "Custom Field SR.aig_reason_note")

frappe.db.commit()

# ============================================ Workflow State / Action masters
NEW_STATES = ["Pending Store Review", "Pending Enterprise Approval",
              "Pending Inspection", "Pending GSK Approval", "Pending Property Assignment",
              "Pending Main Store Approval", "Posted"]
for s in NEW_STATES + ["Draft", "Approved", "Rejected"]:
    get_or_create("Workflow State", {"workflow_state_name": s},
                  {"doctype": "Workflow State", "workflow_state_name": s}, f"Workflow State {s}")

NEW_ACTIONS = ["Submit Request", "Start Receiving", "Record Inspection", "Assign Bins",
               "Assign Bins & Post", "Final Approve & Post", "Post Movement"]
for a in NEW_ACTIONS + ["Approve", "Reject"]:
    get_or_create("Workflow Action Master", {"workflow_action_name": a},
                  {"doctype": "Workflow Action Master", "workflow_action_name": a}, f"Workflow Action {a}")

# ==================================================== Workflow: Material Request
MR_STATES = [
    {"state": "Draft", "doc_status": "0", "allow_edit": "AIG End User"},
    {"state": "Pending Store Review", "doc_status": "1", "allow_edit": "AIG Main Store Administrator"},
    {"state": "Pending Enterprise Approval", "doc_status": "1", "allow_edit": "AIG Enterprise Head"},
    {"state": "Approved", "doc_status": "1", "allow_edit": "System Manager"},
    {"state": "Rejected", "doc_status": "2", "allow_edit": "System Manager"},
]
MR_TRANSITIONS = [
    # Inventory (Material Issue) request path
    {"state": "Draft", "action": "Submit Request", "next_state": "Pending Store Review",
     "allowed": "AIG End User", "condition": 'doc.material_request_type == "Material Issue"'},
    {"state": "Pending Store Review", "action": "Approve", "next_state": "Pending Enterprise Approval",
     "allowed": "AIG Main Store Administrator", "condition": None},
    {"state": "Pending Store Review", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG Main Store Administrator", "condition": None},
    {"state": "Pending Enterprise Approval", "action": "Approve", "next_state": "Approved",
     "allowed": "AIG Enterprise Head", "condition": None},
    {"state": "Pending Enterprise Approval", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG Enterprise Head", "condition": None},
    # Pass-through so non-inventory (e.g. Purchase) MRs stay usable
    {"state": "Draft", "action": "Submit Request", "next_state": "Approved",
     "allowed": "AIG Procurement Officer", "condition": 'doc.material_request_type != "Material Issue"'},
]


def build_mr_workflow():
    name = "AIG Stock Request Approval"
    if frappe.db.exists("Workflow", name):
        log("EXISTS", f"Workflow {name}")
        return
    insert_doc({
        "doctype": "Workflow", "workflow_name": name, "document_type": "Material Request",
        "workflow_state_field": "workflow_state", "is_active": 1, "override_status": 1,
        "send_email_alert": 0,
        "states": MR_STATES,
        "transitions": [{"state": t["state"], "action": t["action"], "next_state": t["next_state"],
                         "allowed": t["allowed"], "condition": t.get("condition") or None}
                        for t in MR_TRANSITIONS],
    }, f"Workflow {name}")


build_mr_workflow()

# ======================================================= Workflow: Stock Entry
# All approval states are docstatus 0 so stock is NOT posted until "Posted".
SE_STATES = [
    {"state": "Draft", "doc_status": "0", "allow_edit": "AIG Store Keeper"},
    {"state": "Pending Inspection", "doc_status": "0", "allow_edit": "AIG Store Keeper"},
    {"state": "Pending GSK Approval", "doc_status": "0", "allow_edit": "AIG General Store Keeper"},
    {"state": "Pending Property Assignment", "doc_status": "0", "allow_edit": "AIG Property Admin Expert"},
    {"state": "Pending Main Store Approval", "doc_status": "0", "allow_edit": "AIG Main Store Administrator"},
    {"state": "Posted", "doc_status": "1", "allow_edit": "System Manager"},
    {"state": "Rejected", "doc_status": "0", "allow_edit": "System Manager"},
]
SE_TRANSITIONS = [
    # Receiving (Material Receipt) path
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
    {"state": "Pending Property Assignment", "action": "Assign Bins & Post", "next_state": "Posted",
     "allowed": "AIG Property Admin Expert", "condition": "not doc.aig_needs_main_approval"},
    {"state": "Pending Property Assignment", "action": "Assign Bins", "next_state": "Pending Main Store Approval",
     "allowed": "AIG Property Admin Expert", "condition": "doc.aig_needs_main_approval == 1"},
    {"state": "Pending Property Assignment", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG Property Admin Expert", "condition": None},
    {"state": "Pending Main Store Approval", "action": "Final Approve & Post", "next_state": "Posted",
     "allowed": "AIG Main Store Administrator", "condition": None},
    {"state": "Pending Main Store Approval", "action": "Reject", "next_state": "Rejected",
     "allowed": "AIG Main Store Administrator", "condition": None},
    # All other purposes (Issue / Transfer / adjustment) post directly - the
    # controlling approval already happened on the Material Request.
    {"state": "Draft", "action": "Post Movement", "next_state": "Posted",
     "allowed": "AIG Store Keeper", "condition": 'doc.purpose != "Material Receipt"'},
]


def build_se_workflow():
    name = "AIG Store Receiving"
    if frappe.db.exists("Workflow", name):
        log("EXISTS", f"Workflow {name}")
        return
    insert_doc({
        "doctype": "Workflow", "workflow_name": name, "document_type": "Stock Entry",
        "workflow_state_field": "workflow_state", "is_active": 1, "override_status": 1,
        "send_email_alert": 0,
        "states": SE_STATES,
        "transitions": [{"state": t["state"], "action": t["action"], "next_state": t["next_state"],
                         "allowed": t["allowed"], "condition": t.get("condition") or None}
                        for t in SE_TRANSITIONS],
    }, f"Workflow {name}")


build_se_workflow()

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP33_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
