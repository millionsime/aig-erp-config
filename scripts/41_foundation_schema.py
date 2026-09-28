# AIG foundation - step 41: schema + reference introspection (read-only).
print("=== ACCOUNTS SETTINGS: cost-center-related fields ===")
for f in frappe.get_meta("Accounts Settings").fields:
    if "cost_center" in (f.fieldname or "") or "balance" in (f.label or "").lower():
        print(f.fieldname, "|", f.label, "| type:", f.fieldtype)
cur = frappe.get_single("Accounts Settings")
for fn in frappe.get_meta("Accounts Settings").get_fieldnames_with_value():
    if "cost_center" in fn:
        print("value:", fn, "=", getattr(cur, fn, None))

print("\n=== BUDGET META ===")
for f in frappe.get_meta("Budget").fields:
    if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Tab Break", "Table"):
        print(f.fieldname, "|", f.label)
print("-- accounts child:")
for f in frappe.get_meta("Budget Account").fields:
    print("   ", f.fieldname, "|", f.label)

print("\n=== EXISTING BUDGET DOCS ===")
names = frappe.get_all("Budget", pluck="name")
for n in names:
    b = frappe.get_doc("Budget", n)
    print(n, "| cost_center:", b.get("cost_center"), "| from:", b.get("from_date"), "to:", b.get("to_date"),
          "| fy:", b.get("fiscal_year"), "| docstatus:", b.docstatus,
          "| against:", b.get("budget_against"), "| annual action:", b.get("action_if_annual_exceeded"),
          "| monthly action:", b.get("action_if_exceeded"))
    for a in b.get("accounts") or []:
        print("    acct:", a.get("account"), a.get("budget_amount"))

print("\n=== ACCOUNTING DIMENSION META ===")
for f in frappe.get_meta("Accounting Dimension").fields:
    print(f.fieldname, "|", f.label, "|", f.fieldtype)
print("-- child 'Accounting Dimension Detail':")
for f in frappe.get_meta("Accounting Dimension Detail").fields:
    print("   ", f.fieldname, "|", f.label, "|", f.fieldtype)

print("\n=== FISCAL YEAR META (company link?) ===")
print([f.fieldname for f in frappe.get_meta("Fiscal Year").fields if f.fieldtype not in ("Section Break", "Column Break")])

print("\n=== COMPANY CC/BANK DEFAULTS ===")
c = frappe.get_doc("Company", "Adama Investment Group")
for fn in ["default_cost_center", "default_bank_account", "default_cash_account", "default_receivable_account",
           "default_payable_account", "default_income_account", "default_expense_account",
           "depreciation_expense_account", "accumulated_depreciation_account", "disposal_account",
           "capital_work_in_progress_account", "default_inventory_account", "stock_received_but_not_billed",
           "default_payroll_payable_account", "round_off_account", "write_off_account",
           "exchange_gain_loss_account", "unrealized_exchange_gain_loss_account", "payment_terms_template"]:
    print(fn, "=", c.get(fn))

print("\n=== COST CENTER USAGE (GL entries per CC) ===")
for r in frappe.db.sql("""select cost_center, count(*) n from `tabGL Entry`
                          where cost_center is not null and cost_center != ''
                          group by cost_center order by n desc""", as_dict=True):
    print(r.cost_center, "->", r.n)

print("\n=== DRAFT POs: native cost_center set? ===")
for po in frappe.get_all("Purchase Order", fields=["name", "docstatus", "cost_center"]):
    print(po)

print("\n=== SERVER SCRIPT: AIG - PO Cost Center Default ===")
ss = frappe.db.get_value("Server Script", {"name": "AIG - PO Cost Center Default"}, "script")
print(ss or "NOT FOUND")

print("\n=== CLIENT SCRIPTS (existing) ===")
print(frappe.get_all("Client Script", fields=["name", "dt", "enabled"]))

print("\n=== ASSET MODULE STATE ===")
print("asset categories:", frappe.get_all("Asset Category", pluck="name"))
print("assets:", frappe.get_all("Asset", fields=["name", "asset_category", "cost_center", "docstatus"], limit=10))
print("asset movement/journal from depreciation:", frappe.db.count("Journal Entry", {"voucher_type": "Depreciation Entry"}))

print("\n=== ASSET CATEGORY ACCOUNTS (first category) ===")
for ac in frappe.get_all("Asset Category", limit=3, pluck="name"):
    d = frappe.get_doc("Asset Category", ac)
    print(ac)
    for fa in d.get("finance_books") or []:
        print("   finance_book:", fa.get("finance_book"), "| dep method:", fa.get("depreciation_method"),
              "| life:", fa.get("total_number_of_depreciations"), "| freq:", fa.get("frequency_of_depreciation"))
    for a in d.get("asset_category_accounts") or []:
        print("   acct map:", a.get("company_name"), "| fixed:", a.get("fixed_asset_account"),
              "| accdep:", a.get("accumulated_depreciation_account"), "| dep exp:", a.get("depreciation_expense_account"),
              "| cwip:", a.get("capital_work_in_progress_account"))

print("\n=== COMPANY LIST (confirm single) ===")
print(frappe.get_all("Company", pluck="name"))

print("\n=== ETHIOPIAN-DATE CLIENT SCRIPT / CUSTOM FIELDS (existing?) ===")
print("custom fields with eth:", frappe.get_all("Custom Field", filters=[["fieldname", "like", "%eth%"]], pluck="name"))
print("client scripts count:", frappe.db.count("Client Script"))

print("\n=== CUSTOM APPS on bench (for hosting client-script JS libs) ===")
import subprocess
print(subprocess.run(["ls", "/home/frappe/frappe-bench/apps"], capture_output=True, text=True).stdout)

print("\nDONE-41")
