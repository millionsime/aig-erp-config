# AIG config - step 40b: diagnose the Material Request submit PermissionError.
import frappe
import traceback
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
ABBR = "AIG"
ITEM = "AIG-INV-FEED"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
DAIRY_CC = f"Dairy Farm - {ABBR}"
U_ENDUSER = "enduser.agro@aig.local"

print("=== Custom DocPerm rows for Material Request ===")
for r in frappe.get_all("Custom DocPerm", filters={"parent": "Material Request"},
                        fields=["role", "read", "write", "create", "submit", "cancel", "amend", "permlevel"]):
    print(r)

print("\n=== roles of enduser.agro ===")
u = frappe.get_doc("User", U_ENDUSER)
print([r.role for r in u.roles])

print("\n=== active workflow for Material Request ===")
wf = frappe.get_all("Workflow", filters={"document_type": "Material Request", "is_active": 1}, pluck="name")
print(wf)
if wf:
    w = frappe.get_doc("Workflow", wf[0])
    print("states:", [(s.state, s.doc_status, s.allow_edit) for s in w.states])
    print("transitions:", [(t.state, t.action, t.next_state, t.allowed, t.condition) for t in w.transitions])

print("\n=== simulate enduser submit ===")
frappe.set_user(U_ENDUSER)
try:
    mr = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": DAIRY_CC,
        "items": [{"item_code": ITEM, "qty": 2, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mr.insert()
    print("inserted:", mr.name)
    print("has submit perm:", frappe.has_permission("Material Request", ptype="submit", doc=mr, throw=False))
    print("transitions available:", [t.get("action") for t in frappe.model.workflow.get_transitions(mr)])
    apply_workflow(mr, "Submit Request")
    frappe.db.commit()
    mr.reload()
    print("state after:", mr.workflow_state, "docstatus", mr.docstatus)
except Exception:
    print("EXCEPTION:")
    print(traceback.format_exc())
finally:
    frappe.set_user("Administrator")

print("\nDIAG_DONE")
