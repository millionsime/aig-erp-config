# 171_finance_po_perm_probe.py -- READ-ONLY: can AIG Finance actually execute
# the "Finance Sign-off" workflow action on Purchase Order? (role-level perms)
import frappe
from frappe.model.workflow import get_transitions

def log(*a):
    print(*a, flush=True)

log("has_permission(Purchase Order, write) as finance:")
frappe.set_user("finance@aig.local")
log("  write:", frappe.has_permission("Purchase Order", "write", throw=False))
log("  submit:", frappe.has_permission("Purchase Order", "submit", throw=False))
log("  read:", frappe.has_permission("Purchase Order", "read", throw=False))
log("  cancel:", frappe.has_permission("Purchase Order", "cancel", throw=False))

# transitions on the waiting PO-3 (direct-purchase path)
po3 = frappe.db.get_value("Purchase Order",
                          {"workflow_state": "Pending Finance Signoff"}, "name")
log("PO at Pending Finance Signoff:", po3)
if po3:
    doc = frappe.get_doc("Purchase Order", po3)
    ts = get_transitions(doc)
    log("transitions for finance:", [(t.action, t.state) for t in ts])

frappe.set_user("Administrator")
log("")
log("Custom DocPerm rows on Purchase Order mentioning finance roles:")
for r in frappe.get_all("Custom DocPerm", filters={"parent": "Purchase Order"},
                        fields=["role", "read", "write", "submit", "cancel", "amend"],
                        order_by="role"):
    log(" ", r)
log("")
log("Standard DocPerm roles on Purchase Order:")
for r in frappe.get_all("DocPerm", filters={"parent": "Purchase Order"},
                        fields=["role", "write", "submit"], order_by="role"):
    log(" ", r)
log("DONE")
