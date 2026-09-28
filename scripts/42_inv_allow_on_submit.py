# AIG config - step 42: allow post-submission edits on workflow-driven fields.
#
# ROOT CAUSE (verified in step 40/42a):
#   The Stock Request approval workflow keeps Material Request at docstatus 1 while
#   it moves through "Pending Store Review" -> "Pending Enterprise Approval". The
#   store administrator must record the budget check, and the end user must confirm
#   receipt, AFTER submission. Frappe's validate_update_after_submit blocks any
#   changed field that is not flagged allow_on_submit -> UpdateAfterSubmitError.
#
# CONFIG-LAYER FIX (no core edits): set allow_on_submit=1 on the AIG custom fields
# that are legitimately edited during post-submission workflow steps. Editing is
# still governed by Custom DocPerms + the "AIG - MR Approval Guard" server script
# (self-approval block + honest budget recording). Idempotent.
import frappe
import traceback

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def set_allow_on_submit(dt, fieldname):
    cf_name = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": fieldname}, "name")
    if not cf_name:
        log("FLAG", f"Custom Field missing: {dt}.{fieldname}")
        return
    cur = frappe.db.get_value("Custom Field", cf_name, "allow_on_submit")
    if cur:
        log("EXISTS", f"allow_on_submit already set: {dt}.{fieldname}")
        return
    try:
        cf = frappe.get_doc("Custom Field", cf_name)
        cf.allow_on_submit = 1
        cf.flags.ignore_permissions = True
        cf.save(ignore_permissions=True)
        log("UPDATE", f"allow_on_submit=1 -> {dt}.{fieldname}")
    except Exception:
        print(f"!! FAILED {dt}.{fieldname}")
        print(traceback.format_exc())


# Material Request fields edited after submission (store review + receipt confirm)
for f in ["aig_budget_checked", "aig_budget_note", "aig_issue_reference",
          "aig_received_by", "aig_received_on", "aig_receipt_confirmed", "aig_receipt_note"]:
    set_allow_on_submit("Material Request", f)

# Stock Entry fields that may be completed while the doc is in a workflow state
for f in ["aig_inspected_by", "aig_inspection_notes", "aig_issued_to"]:
    set_allow_on_submit("Stock Entry", f)

frappe.db.commit()
frappe.clear_cache(doctype="Material Request")
frappe.clear_cache(doctype="Stock Entry")
print(f"\nSTEP42_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
