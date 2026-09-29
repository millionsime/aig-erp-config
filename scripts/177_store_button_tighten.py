# 177_store_button_tighten.py -- PATCH (commits on success): Pending Store
# Review buttons become type-scoped so the store admin sees exactly ONE
# approve button per request type:
#   Purchase       -> only "Approve & Assign" (assignment enforced)
#   Material Issue -> only "Approve" (original enterprise-approval route)
import frappe

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")
w = frappe.get_doc("Workflow", "AIG Stock Request Approval")
for t in w.transitions:
    if (t.state == "Pending Store Review" and t.action == "Approve"
            and t.next_state == "Pending Enterprise Approval"):
        t.condition = 'doc.material_request_type == "Material Issue"'
        log("scoped: store Approve -> Material Issue only")
    if t.state == "Pending Store Review" and t.action == "Approve & Assign":
        t.condition = ('doc.material_request_type == "Purchase" and '
                       'doc.aig_assigned_procurement_officer')
        log("scoped: Approve & Assign -> Purchase + officer assigned")
w.save(ignore_permissions=True)
frappe.clear_cache()
log("DONE 177")
