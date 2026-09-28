# 26 - Fix the Account read gap that blocks Payment Entry / Purchase Invoice forms
# for AIG approvers (erpnext get_party_account throws PermissionError otherwise).
# Also removes orphaned Custom DocPerm rows (parent NULL) left by the old dt->parent bug.
import frappe
from erpnext.accounts.party import get_party_account

COMPANY = "Adama Investment Group"
SUPPLIER = "Ethio Dairy Supplies PLC"

# 1) delete orphaned Custom DocPerm rows (engine-invisible, from the old dt bug)
orphans = set(frappe.get_all("Custom DocPerm", filters=[["parent", "is", "not set"]], pluck="name"))
orphans |= set(frappe.get_all("Custom DocPerm", filters={"parent": ""}, pluck="name"))
for name in orphans:
    frappe.delete_doc("Custom DocPerm", name, ignore_permissions=True)
print(f"deleted {len(orphans)} orphaned Custom DocPerm rows (parent NULL)")


def perm_read(dt, role, permlevel=0):
    filters = {"parent": dt, "role": role, "permlevel": permlevel}
    if frappe.db.exists("Custom DocPerm", filters):
        return "exists"
    frappe.get_doc({
        "doctype": "Custom DocPerm", "parent": dt, "role": role, "permlevel": permlevel,
        "read": 1, "write": 0, "create": 0, "submit": 0, "cancel": 0, "amend": 0,
    }).insert(ignore_permissions=True)
    return "created"


# 2) grant Account (permlevel 0) read to every AIG approver role that lacked it
NEED_ACCOUNT = ["AIG Deputy", "AIG CEO", "AIG Enterprise Head",
                "AIG Purchase Committee", "AIG Evaluation Committee"]
for r in NEED_ACCOUNT:
    print(f"  Account read -> {r}: {perm_read('Account', r)}")

frappe.db.commit()

# 3) verify: each approver can now resolve the party account without a throw
CHECK = {
    "finance@aig.local": "Payment Entry",
    "deputy@aig.local": "Payment Entry",
    "corporate@aig.local": "Payment Entry",
    "ceo@aig.local": "Payment Entry",
    "committee1@aig.local": "Purchase Invoice",
    "head.agro@aig.local": "Purchase Invoice",
}
print("\n=== verify get_party_account (the call that was throwing) ===")
for user in CHECK:
    frappe.set_user(user)
    try:
        acct = get_party_account("Supplier", SUPPLIER, COMPANY)
        print(f"  [OK]    {user:32s} -> party account {acct}")
    except Exception as e:
        print(f"  [THROW] {user:32s} -> {type(e).__name__}: {str(e)[:120]}")
    frappe.set_user("Administrator")

# 4) verify Account read on the three concrete accounts used by the demo docs
print("\n=== verify read on concrete demo accounts ===")
ACCOUNTS = ["Creditors - AIG", "Commercial Bank of Ethiopia - AIG", "Cost of Goods Sold - AIG"]
for user in ["deputy@aig.local", "ceo@aig.local", "committee1@aig.local", "head.agro@aig.local"]:
    frappe.set_user(user)
    res = {a: bool(frappe.has_permission("Account", "read", doc=a, throw=False)) for a in ACCOUNTS}
    frappe.set_user("Administrator")
    print(f"  {user:32s} {res}")

print("\nFIX_ACCOUNT_DONE")
