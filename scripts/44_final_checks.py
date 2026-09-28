# AIG foundation - step 44: final targeted checks (read-only).
import subprocess

BASE = "/home/frappe/frappe-bench/apps"

def run(label, *args):
    print(f"\n=== {label} ===")
    r = subprocess.run(list(args), capture_output=True, text=True)
    print(r.stdout[:4000] or "(no output)")

run("allow_cost_center_in_entries_of_bs_account anywhere in erpnext?",
    "grep", "-rl", "allow_cost_center_in_entries_of_bs_account", f"{BASE}/erpnext")
run("allow_st_cost_center variant?",
    "grep", "-rl", "allow_st_cost_center", f"{BASE}/erpnext")
run("accounts_settings.json: all fieldnames with 'center' or 'balanc'",
    "grep", "-o", '"fieldname": "[a-z_]*"', f"{BASE}/erpnext/erpnext/accounts/doctype/accounts_settings/accounts_settings.json")
run("get_checks_for_pl_and_bs_accounts definition",
    "grep", "-n", "-A", "40", "def get_checks_for_pl_and_bs_accounts",
    f"{BASE}/erpnext/erpnext/accounts/doctype/accounting_dimension/accounting_dimension.py")
run("Cost Center dimension pre-exists? (db)",
    "grep", "-c", "x", "/dev/null")

# DB-side checks via frappe
print("\n=== DB: Accounting Dimension rows ===")
print(frappe.get_all("Accounting Dimension", fields=["name", "document_type", "fieldname", "disabled"]))
print("\n=== DB: Dimension defaults rows ===")
print(frappe.get_all("Accounting Dimension Detail", fields=["parent", "company", "mandatory_for_bs", "mandatory_for_pl", "default_dimension"]))
print("\n=== DB: Accounts Settings doc fieldnames containing 'center' ===")
asd = frappe.get_doc("Accounts Settings")
print([fn for fn in asd.as_dict() if "center" in fn])
print("\n=== DB: Cost Center dimension defaults via get_dimensions() ===")
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions, get_checks_for_pl_and_bs_accounts
try:
    print(get_dimensions())
except Exception as e:
    print("get_dimensions error:", e)
try:
    print(get_checks_for_pl_and_bs_accounts())
except Exception as e:
    print("get_checks error:", e)

print("\n=== DB: GL entries sample (cost centers on BS accounts?) ===")
for r in frappe.db.sql("""select account, cost_center, sum(debit)-sum(credit) bal
                          from `tabGL Entry` group by account, cost_center
                          order by account limit 30""", as_dict=True):
    print(r)

print("\n=== DB: fiscal year companies child table ===")
print(frappe.get_all("Fiscal Year Company", fields=["parent", "company"]))
print("\nDONE-44")
