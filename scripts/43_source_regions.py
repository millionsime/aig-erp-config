# AIG foundation - step 43: read exact v16 source regions (READ-ONLY sed prints).
import subprocess

APPS = "/home/frappe/frappe-bench/apps"

def sed(path, a, b, label):
    print(f"\n=== {label} ({path}:{a}-{b}) ===")
    r = subprocess.run(["sed", "-n", f"{a},{b}p", f"{APPS}/{path}"], capture_output=True, text=True)
    print(r.stdout)

def grep(label, *args):
    print(f"\n=== {label} ===")
    r = subprocess.run(["grep", "-rn", *args, f"{APPS}/erpnext/erpnext"], capture_output=True, text=True)
    print(r.stdout[:5000] or "(no matches)")

sed("erpnext/erpnext/assets/doctype/asset/depreciation.py", 230, 330, "DEPRECIATION DIMENSION HANDLING")
sed("erpnext/erpnext/accounts/doctype/gl_entry/gl_entry.py", 180, 300, "GL ENTRY: dimension mandatory + validate_cost_center")
sed("erpnext/erpnext/accounts/doctype/accounting_dimension/accounting_dimension.py", 1, 140, "ACCOUNTING DIMENSION doc + helpers")
sed("erpnext/erpnext/accounts/doctype/accounting_dimension/accounting_dimension.py", 140, 320, "ACCOUNTING DIMENSION get_dimensions etc")
grep("allow_cost_center... (all files)", "-l", "allow_cost_center_in_entries_of_bs_account")
grep("allow_st_cost_center (variant)", "allow_st_cost_center")
grep("balance_sheet.js cost center filter", "cost_center", "erpnext/accounts/report/balance_sheet/balance_sheet.js")
grep("financial statements cost center filter", "-l", "cost_center", "erpnext/accounts/report/financial_statement")
grep("get_dimension_with_company / mandatory helpers", "def get_dimension_with_company\\|mandatory_for_bs")
sed("erpnext/erpnext/assets/doctype/asset/asset.py", 345, 375, "ASSET validate_cost_center")
grep("asset depreciation schedule cost_center default", "cost_center", "erpnext/assets/doctype/asset_depreciation_schedule/asset_depreciation_schedule.py")
grep("journal entry accounts depreciation cost_center", "cost_center", "erpnext/accounts/doctype/journal_entry/journal_entry.py")

print("\nDONE-43")
