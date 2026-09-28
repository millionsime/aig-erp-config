# AIG foundation brief - step 40: read-only inspection for the FOUNDATION layer.
print("=== COMPANY ===")
for c in frappe.get_all("Company", fields=["name", "company_name", "abbr", "default_currency",
                                           "country", "domain", "chart_of_accounts",
                                           "enable_perpetual_inventory"]):
    print(c)

print("\n=== FISCAL YEARS ===")
for fy in frappe.get_all("Fiscal Year", fields=["name", "year_start_date", "year_end_date", "disabled"]):
    print(fy)

print("\n=== ACCOUNTS SUMMARY ===")
total = frappe.db.count("Account")
groups = frappe.db.count("Account", {"is_group": 1})
print(f"total accounts: {total}  (groups: {groups}, leaves: {total - groups})")
print("root accounts:")
for a in frappe.get_all("Account", filters={"parent_account": ["is", "not set"], "is_group": 1},
                        fields=["name", "root_type", "account_type"]):
    print("  ", a)

print("\n=== TOP-LEVEL ACCOUNT TREE (depth<=2) ===")
root_names = frappe.get_all("Account", filters={"parent_account": ["is", "not set"]}, pluck="name")
for a in frappe.get_all("Account",
                        filters=[[ "parent_account", "in", root_names ]],
                        fields=["name", "account_name", "root_type", "account_type", "is_group"],
                        order_by="lft"):
    print(f"  [G] {a.name}" if a.is_group else f"      {a.name}")

print("\n=== RETAINED EARNINGS / PAID UP / CONTROL CANDIDATES ===")
for pat in ["Retained", "Paid", "Capital", "Debtor", "Creditor", "Staff", "Salary", "Salaries",
            "Depreciation", "Bank Service", "Bank Charge"]:
    accs = frappe.get_all("Account", filters=[["account_name", "like", f"%{pat}%"]],
                          fields=["name", "is_group", "root_type"], limit=12)
    if accs:
        print(f"-- {pat} ({len(accs)}):")
        for a in accs:
            print("   ", a.name, "[G]" if a.is_group else "")

print("\n=== COST CENTER TREE ===")
for cc in frappe.get_all("Cost Center", filters={"disabled": 0},
                         fields=["name", "cost_center_name", "parent_cost_center", "company", "is_group"],
                         order_by="lft"):
    print(f"{'[G]' if cc.is_group else '   '} {cc.name}  parent={cc.parent_cost_center}")

print("\n=== ACCOUNTING DIMENSIONS ===")
try:
    for d in frappe.get_all("Accounting Dimension", fields=["name", "disabled", "fieldname"]):
        print(d)
        docs = frappe.get_all("Accounting Dimension Detail",
                              filters={"parent": d.name},
                              fields=["document_type", "mandatory_for"])
        for x in docs:
            print("    ", x)
except Exception as e:
    print("Accounting Dimension read error:", e)

print("\n=== ACCOUNTS SETTINGS (relevant) ===")
import json
as_doc = frappe.get_doc("Accounts Settings")
for f in ["allow_cost_center_in_entries_of_bs_account", "allow_multi_currency_invoices_and_vouchers",
          "auto_accounting_for_stock_settings", "book_deferred_entries_based_on", "default_inventory_account"]:
    print(f, "=", getattr(as_doc, f, "<not-present>"))

print("\n=== GLOBAL DEFAULTS ===")
gd = frappe.get_doc("Global Defaults")
print("default_currency:", gd.default_currency)
print("default_company:", gd.default_company)

print("\n=== BUDGETS ===")
for b in frappe.get_all("Budget", fields=["name", "cost_center", "fiscal_year", "company", "docstatus",
                                          "budget_against", "action_if_annual_exceeded"]):
    print(b)

print("\n=== FIXED ASSET / DEPRECIATION QUICK STATE ===")
print("assets:", frappe.db.count("Asset"))
print("asset depreciation schedules:", frappe.db.count("Asset Depreciation Schedule"))
print("journal entries:", frappe.db.count("Journal Entry Account"))

print("\n=== ERPNEXT VERSION ===")
import erpnext
print(getattr(erpnext, "__version__", "unknown"))

print("\n=== INSTALLED APPS ===")
print(frappe.get_installed_apps())

print("\nDONE-40")
