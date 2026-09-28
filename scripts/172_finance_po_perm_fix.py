# 172_finance_po_perm_fix.py -- FIX (commits on success): AIG Finance must be
# able to EXECUTE the "Finance Sign-off" workflow action on Purchase Order.
# The workflow transition exists (Pending Finance Signoff -> Approved) but the
# role's Custom DocPerm is read-only, so apply_workflow's doc.save() throws
# PermissionError - the button would bounce in the live GUI too.
import frappe

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")

row = frappe.db.get_value("Custom DocPerm",
                          {"parent": "Purchase Order", "role": "AIG Finance"},
                          "name")
if not row:
    raise Exception("Custom DocPerm (Purchase Order / AIG Finance) not found")

perm = frappe.get_doc("Custom DocPerm", row)
log("before:", perm.role, "read", perm.read, "write", perm.write,
    "submit", perm.submit, "cancel", perm.cancel)
perm.write = 1
perm.submit = 1
# finance signs off; cancel/amend stay with procurement + approvers
perm.save(ignore_permissions=True)
log("after: ", perm.role, "read", perm.read, "write", perm.write,
    "submit", perm.submit, "cancel", perm.cancel)

# verify the whole action is now executable as finance
frappe.set_user("finance@aig.local")
ok_w = frappe.has_permission("Purchase Order", "write", throw=False)
ok_s = frappe.has_permission("Purchase Order", "submit", throw=False)
frappe.set_user("Administrator")
if not (ok_w and ok_s):
    raise Exception("Finance still lacks write/submit on Purchase Order")
log("finance write:", ok_w, "submit:", ok_s)
log("DONE")
