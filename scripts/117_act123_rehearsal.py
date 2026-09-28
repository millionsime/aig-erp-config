# 117_act123_rehearsal.py -- Re-run Act 1-3 rehearsal (MR create + Submit
# Request + storeadmin Approve + head Approve) with the real demo item, dump
# the FULL traceback if any step fails (116 showed only the last line), then
# delete the rehearsal MR.

import traceback

import frappe
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
ENDUSER = "enduser.agro@aig.local"
STOREADMIN = "storeadmin.agro@aig.local"
HEAD = "head.agro@aig.local"
ITEM = "AIG-INV-FEED"
WH = "Dairy Farm Store - AIG"


def log(*a):
    print(*a, flush=True)


mr_name = None
try:
    frappe.set_user(ENDUSER)
    mr = frappe.new_doc("Material Request")
    mr.company = COMPANY
    mr.material_request_type = "Material Issue"
    mr.schedule_date = frappe.utils.add_days(frappe.utils.nowdate(), 2)
    mr.aig_budget_note = "Rehearsal for Saturday demo"
    mr.append("items", {"item_code": ITEM, "qty": 2, "schedule_date":
                        mr.schedule_date, "warehouse": WH})
    mr.insert()
    mr_name = mr.name
    log(f"created: {mr_name} (state={mr.workflow_state}, type={mr.material_request_type})")

    apply_workflow(mr, "Submit Request")
    log(f"enduser Submit Request -> {mr.workflow_state} (docstatus={mr.docstatus})")

    frappe.set_user(STOREADMIN)
    mr = frappe.get_doc("Material Request", mr_name)
    apply_workflow(mr, "Approve")
    log(f"storeadmin Approve     -> {mr.workflow_state} (docstatus={mr.docstatus})")

    frappe.set_user(HEAD)
    mr = frappe.get_doc("Material Request", mr_name)
    apply_workflow(mr, "Apply Workflow Action")
    log(f"head 'Apply Workflow Action' -> {mr.workflow_state} (docstatus={mr.docstatus})")

    log("")
    log("ACT 1-3 REHEARSAL: ALL GREEN")
except Exception:
    log("REHEARSAL FAILED -- full traceback:")
    log(traceback.format_exc())
finally:
    frappe.set_user("Administrator")
    if mr_name and frappe.db.exists("Material Request", mr_name):
        d = frappe.get_doc("Material Request", mr_name)
        if d.docstatus == 1:
            try:
                d.cancel()
            except Exception:
                pass
        frappe.delete_doc("Material Request", mr_name,
                          ignore_permissions=True, force=True)
        log(f"cleaned up rehearsal MR {mr_name}")
