# AIG config - step 47: INVENTORY saved-view reports (config layer, no core edits).
# Creates Report Builder reports for the AIG-specific views the brief asks for that
# the built-in stock reports do not cover. Report Builder reports run through the
# standard ORM list query, so they RESPECT Cost Center / Warehouse User Permissions
# and Custom DocPerms automatically (no cross-enterprise leakage). Each report is
# validated here by running an equivalent get_list so a bad filter/field fails loudly.
import frappe
import json
import traceback

MODULE = "Stock"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def make_json(ref_doctype, columns, filters, sort_by=None):
    return json.dumps({
        "add_total_row": 0,
        "add_totals_row": 0,
        "sort_by": sort_by or f"{ref_doctype}.modified",
        "sort_order": "desc",
        "sort_by_next": None,
        "sort_order_next": "desc",
        "filters": filters,
        "columns": [[c, ref_doctype] for c in columns],
    })


def build_report(name, ref_doctype, columns, filters, sort_by=None):
    js = make_json(ref_doctype, columns, filters, sort_by)
    if frappe.db.exists("Report", name):
        rep = frappe.get_doc("Report", name)
        rep.json = js
        rep.ref_doctype = ref_doctype
        rep.report_type = "Report Builder"
        rep.module = MODULE
        rep.is_standard = "No"
        rep.disabled = 0
        rep.flags.ignore_permissions = True
        rep.save(ignore_permissions=True)
        log("UPDATE", f"Report {name}")
    else:
        rep = frappe.get_doc({
            "doctype": "Report", "report_name": name, "ref_doctype": ref_doctype,
            "report_type": "Report Builder", "module": MODULE, "is_standard": "No",
            "json": js, "disabled": 0,
        })
        rep.flags.ignore_permissions = True
        try:
            rep.insert(ignore_permissions=True)
            log("CREATE", f"Report {name}")
        except Exception:
            print(f"!! FAILED create {name}")
            print(traceback.format_exc())
            return
    # validate: run an equivalent list query as admin (schema/filter check only)
    try:
        frappe.get_list(ref_doctype, filters=filters,
                        fields=columns, limit=5, ignore_permissions=True)
        log("VALIDATE", f"Report {name} query OK")
    except Exception:
        print(f"!! VALIDATE FAILED {name}")
        print(traceback.format_exc())


OPEN_STATES = ["Draft", "Pending Store Review", "Pending Enterprise Approval"]
RECEIPT_STATES = ["Draft", "Pending Inspection", "Pending GSK Approval",
                  "Pending Property Assignment", "Pending Main Store Approval"]

# 1) Outstanding (not yet approved/rejected) stock requests
build_report(
    "AIG Outstanding Stock Requests", "Material Request",
    ["name", "aig_cost_center", "aig_requested_by", "workflow_state",
     "schedule_date", "aig_destination_warehouse"],
    [["Material Request", "material_request_type", "=", "Material Issue"],
     ["Material Request", "workflow_state", "in", OPEN_STATES]],
)

# 2) Approved requests awaiting issue fulfilment
build_report(
    "AIG Approved Requests Pending Issue", "Material Request",
    ["name", "aig_cost_center", "aig_requested_by", "schedule_date",
     "aig_issue_reference", "workflow_state"],
    [["Material Request", "material_request_type", "=", "Material Issue"],
     ["Material Request", "workflow_state", "=", "Approved"]],
)

# 3) Receipts still moving through the receiving approvals (not yet Posted)
build_report(
    "AIG Receipts Pending Approval", "Stock Entry",
    ["name", "aig_cost_center", "posting_date", "workflow_state",
     "to_warehouse", "aig_source_ref"],
    [["Stock Entry", "purpose", "=", "Material Receipt"],
     ["Stock Entry", "workflow_state", "in", RECEIPT_STATES]],
)

# 4) Stock counts & adjustments with mandatory reason codes
build_report(
    "AIG Stock Adjustments & Counts", "Stock Reconciliation",
    ["name", "aig_cost_center", "posting_date", "aig_reason_code", "aig_reason_note"],
    [],
)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP47_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
