# 151_reset_demo_mr.py -- The Act 1 demo MR (MAT-MR-2026-00014) was created
# with Purpose = "Material Issue", which routes it into the phase-1
# store-review chain (Pending Store Review) where the Procurement Officer has
# no buttons - and from which the endorsement flow can never start. Cancel
# and delete it so the demo can be redone cleanly with Purpose = Purchase.
import frappe


def log(*a):
    print(*a, flush=True)


NAME = "MAT-MR-2026-00014"
if not frappe.db.exists("Material Request", NAME):
    log(f"{NAME}: not found - nothing to do")
else:
    st = frappe.db.get_value("Material Request", NAME,
                             ["docstatus", "workflow_state"], as_dict=True)
    log(f"{NAME}: docstatus={st.docstatus} state={st.workflow_state!r}")
    if st.docstatus == 1:
        frappe.get_doc("Material Request", NAME).cancel()
        log("  cancelled")
    frappe.delete_doc("Material Request", NAME, force=True,
                      ignore_permissions=True)
    log("  deleted")
leftover = frappe.get_all("AIG Committee Signoff", pluck="name")
log(f"note: unrelated committee sign-off rows present: {len(leftover)}")
log("DONE 151")
