import frappe

PO = "PUR-ORD-2026-00005"
COMMITTEE = "committee1@aig.local"
CROLE = "AIG Purchase Committee"

# 1) What Custom DocPerm rows exist for Account, and for which roles?
print("=== Custom DocPerm on Account ===")
for r in frappe.get_all("Custom DocPerm", filters={"parent": "Account"},
                        fields=["name", "role", "permlevel", "read", "write", "if_owner"],
                        order_by="role, permlevel"):
    print(" ", r)

print("\n=== Does Account have ANY Custom DocPerm? (if yes, defaults are replaced) ===")
print("  count:", frappe.db.count("Custom DocPerm", {"parent": "Account"}))
print("  default DocPerm count:", frappe.db.count("DocPerm", {"parent": "Account"}))

# 2) All Custom DocPerm rows for the committee role
print("\n=== Custom DocPerm rows for role", CROLE, "===")
for r in frappe.get_all("Custom DocPerm", filters={"role": CROLE},
                        fields=["parent", "permlevel", "read", "write", "submit", "if_owner"],
                        order_by="parent"):
    print(" ", r)

# 3) The accounts referenced by the PO
print("\n=== PO line accounts ===")
po = frappe.get_doc("Purchase Order", PO)
print("  company:", po.company)
for it in po.items:
    print("  item", it.item_code, "expense_account:", it.expense_account, "cost_center:", it.cost_center)

# 4) Reproduce the committee's permission checks
frappe.set_user(COMMITTEE)
roles = frappe.get_roles()
print("\ncommittee roles:", [r for r in roles if r.startswith('AIG')] , "| System Manager?", "System Manager" in roles)
try:
    ok = frappe.has_permission("Purchase Order", "read", doc=PO, throw=False)
    print("  read Purchase Order", PO, "->", ok)
except Exception as e:
    print("  PO read error:", e)
# find the specific account that fails
acct = po.items[0].expense_account if po.items else None
if acct:
    try:
        ok = frappe.has_permission("Account", "read", doc=acct, throw=False)
        print("  read Account", acct, "->", ok)
    except Exception as e:
        print("  Account read error:", e)
    try:
        d = frappe.get_doc("Account", acct)
        print("  get_doc Account OK:", d.name)
    except Exception as e:
        print("  get_doc Account FAILED:", type(e).__name__, str(e)[:160])
# try loading the PO fully as committee (this is what the form does)
try:
    d = frappe.get_doc("Purchase Order", PO)
    _ = d.as_dict()
    print("  full PO load as committee: OK")
except Exception as e:
    print("  full PO load as committee FAILED:", type(e).__name__, str(e)[:200])
frappe.set_user("Administrator")

print("\nPERM_DIAG_DONE")
