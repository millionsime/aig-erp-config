# AIG foundation - step 42: read-only source verification of v16 mechanisms.
# GREPS ONLY - no file is modified anywhere.
import subprocess

BASE = "/home/frappe/frappe-bench/apps/erpnext/erpnext"

def g(args, label):
    print(f"\n=== {label} ===")
    r = subprocess.run(["grep", "-rn"] + args + [BASE], capture_output=True, text=True)
    out = r.stdout.strip()
    print(out[:6000] if out else "(no matches)")

g(["-l", "allow_cost_center_in_entries_of_bs_account"], "FILES: allow_cost_center_in_entries_of_bs_account")
g(["allow_cost_center_in_entries_of_bs_account", "--include=*.py"], "PY: allow_cost_center... usage")
g(["allow_st_cost_center_in_entries_of_bs_account", "-r"], "PY: allow_st_cost_center variant")

print("\n=== ACCOUNTS SETTINGS JSON: fieldnames ===")
r = subprocess.run(["grep", "-o", '"fieldname": "[a-z_]*"',
                    BASE + "/accounts/doctype/accounts_settings/accounts_settings.json"],
                   capture_output=True, text=True)
names = [l.split('"')[3] for l in r.stdout.splitlines()]
print([n for n in names if "cost" in n or "center" in n])
print("total settings fields:", len(names))

g(["mandatory_for_bs", "--include=*.py"], "PY: mandatory_for_bs usage (dimension)")
g(["class AccountingDimension", "-A 5", "--include=*.py"], "PY: AccountingDimension validation")
g(["def get_dimensions", "-A 25", "erpnext/accounts/doctype/accounting_dimension/accounting_dimension.py"],
  "PY: get_dimensions()")
g(["validate_cost_center", "--include=*.py"], "PY: validate_cost_center in GL")
g(["cost_center", "erpnext/accounts/doctype/gl_entry/gl_entry.py"], "PY: gl_entry cost_center mentions")

print("\n=== BALANCE SHEET REPORT FILTERS ===")
r = subprocess.run(["grep", "-n", "cost_center",
                    BASE + "/accounts/report/balance_sheet/balance_sheet.py",
                    BASE + "/accounts/report/balance_sheet/balance_sheet.json"],
                   capture_output=True, text=True)
print(r.stdout or "(no cost_center filter in balance_sheet report)")

print("\n=== BUDGET: fiscal year fields on demo budgets (full docs) ===")
for n in frappe.get_all("Budget", pluck="name"):
    b = frappe.get_doc("Budget", n)
    print(n, "| CC:", b.get("cost_center"), "| project:", b.get("project"),
          "| against:", b.get("budget_against"),
          "| FY:", b.get("from_fiscal_year"), "->", b.get("to_fiscal_year"),
          "| annual action:", b.get("action_if_annual_budget_exceeded"),
          "| monthly action:", b.get("action_if_accumulated_monthly_budget_exceeded"),
          "| on PO:", b.get("applicable_on_purchase_order"),
          "| PO action:", b.get("action_if_annual_budget_exceeded_on_po"),
          "| docstatus:", b.docstatus,
          "| accounts:", [(a.account, a.budget_amount) for a in (b.get("accounts") or [])])

print("\n=== GLOBAL DEFAULTS: default fiscal year field? ===")
print([f.fieldname for f in frappe.get_meta("Global Defaults").fields if "fiscal" in f.fieldname])

print("\n=== DEPRECIATION POSTING API (function names) ===")
r = subprocess.run(["grep", "-rn", "def post_depreciation_entries\\|def post_depreciation\\|make_depreciation_entry",
                    BASE + "/assets"], capture_output=True, text=True)
print(r.stdout[:3000] or "(none)")

print("\n=== ASSET: is item_code mandatory? ===")
r = subprocess.run(["grep", "-n", '"reqd"', BASE + "/assets/doctype/asset/asset.json"], capture_output=True, text=True)
print(r.stdout[:1500])

print("\n=== ASSET cost_center field? ===")
r = subprocess.run(["grep", "-n", "cost_center", BASE + "/assets/doctype/asset/asset.json"], capture_output=True, text=True)
print(r.stdout[:1500] or "(no cost_center on Asset)")

g(["cost_center", "erpnext/accounts/doctype/asset_depreciation_schedule/asset_depreciation_schedule.py"],
  "PY: ADS cost_center handling")

print("\nDONE-42")
