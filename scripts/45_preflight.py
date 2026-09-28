# AIG foundation - step 45: preflight (read-only) - pin down build details.
import json
import subprocess

BASE = "/home/frappe/frappe-bench/apps"

print("=== GL ENTRY: cost center validation trigger (lines 140-200) ===")
r = subprocess.run(["sed", "-n", "140,200p", f"{BASE}/erpnext/erpnext/accounts/doctype/gl_entry/gl_entry.py"],
                   capture_output=True, text=True)
print(r.stdout)

print("\n=== COST CENTER: on_rename handler? ===")
r = subprocess.run(["grep", "-n", "def on_rename\\|def on_trash\\|def update_gl", 
                    f"{BASE}/erpnext/erpnext/accounts/doctype/cost_center/cost_center.py"],
                   capture_output=True, text=True)
print(r.stdout or "(none)")

print("\n=== BALANCE SHEET JS: filters (grep cost_center / dimension) ===")
r = subprocess.run(["grep", "-n", "cost_center\\|dimension", f"{BASE}/erpnext/erpnext/accounts/report/balance_sheet/balance_sheet.js"],
                   capture_output=True, text=True)
print(r.stdout or "(no matches)")
r = subprocess.run(["grep", "-n", "cost_center", f"{BASE}/erpnext/erpnext/accounts/report/financial_statement*.py",
                    f"{BASE}/erpnext/erpnext/accounts/report/summary/summary.py",
                    f"{BASE}/erpnext/erpnext/accounts/report/summary/summary.js"], capture_output=True, text=True)
print(r.stdout or "(none in summary either)")

print("\n=== BUDGET VARIANCE REPORT: filters ===")
r = subprocess.run(["ls", f"{BASE}/erpnext/erpnext/accounts/report/"], capture_output=True, text=True)
print([x for x in r.stdout.split() if "udget" in x])
r = subprocess.run(["grep", "-n", "cost_center", f"{BASE}/erpnext/erpnext/accounts/report/budget_variance_report/budget_variance_report.py"],
                   capture_output=True, text=True)
print(r.stdout or "(none)")

print("\n=== USER PERMISSIONS (all) ===")
for up in frappe.get_all("User Permission", fields=["user", "allow", "for_value", "name"]):
    print(up)

print("\n=== BUDGET AMOUNTS (header field) ===")
for n in frappe.get_all("Budget", pluck="name"):
    b = frappe.get_doc("Budget", n)
    print(n, "| amount:", b.get("budget_amount"), "| distribution:", b.get("distribution_frequency"),
          "| start:", b.get("budget_start_date"), "| end:", b.get("budget_end_date"))

print("\n=== KEY ACCOUNT DETAILS ===")
for acc in ["Capital Equipment - AIG", "Accumulated Depreciation - AIG", "Depreciation - AIG",
            "Cash - AIG", "Commercial Bank of Ethiopia - AIG", "Sales - AIG", "Debtors - AIG",
            "Stock In Hand - AIG", "Cost of Goods Sold - AIG", "Head Office - AIG"]:
    d = frappe.db.get_value("Account", acc,
                            ["name", "is_group", "account_type", "root_type", "report_type", "parent_account", "account_number"], as_dict=True)
    print(acc, "->", d)

print("\n=== ACCOUNT TYPE OPTIONS ===")
f = frappe.get_meta("Account").get_field("account_type")
print((f.options or "").split("\n"))

print("\n=== ITEM GROUPS / UOM / CUSTOMERS ===")
print("item groups:", frappe.get_all("Item Group", pluck="name"))
print("uoms:", [u for u in frappe.get_all("UOM", pluck="name")][:15])
print("customers:", frappe.get_all("Customer", pluck="name"))
print("companies for customer group:", frappe.get_all("Customer Group", pluck="name"))
print("territories:", frappe.get_all("Territory", pluck="name"))

print("\n=== ASSET DOCTYPE: reqd fields + finance book child ===")
with open(f"{BASE}/erpnext/erpnext/assets/doctype/asset/asset.json") as fp:
    aj = json.load(fp)
print("reqd:", [f["fieldname"] for f in aj["fields"] if f.get("reqd")])
print("has finance_books:", any(f["fieldname"] == "finance_books" for f in aj["fields"]))
print("fieldname options for location:", [f["fieldname"] for f in aj["fields"] if "location" in f["fieldname"]])
r = subprocess.run(["ls", f"{BASE}/erpnext/erpnext/assets/doctype/"], capture_output=True, text=True)
print("asset child doctypes:", [x for x in r.stdout.split() if "finance" in x or "schedule" in x])

print("\n=== ACCOUNTS SETTINGS: auto dep ===")
print("book_asset_depreciation_entry_automatically:",
      frappe.db.get_single_value("Accounts Settings", "book_asset_depreciation_entry_automatically"))
print("book_asset_depreciation_entry_automatically type:",
      frappe.get_meta("Accounts Settings").get_field("book_asset_depreciation_entry_automatically").fieldtype)

print("\n=== JOURNAL ENTRY: workflow attached? ===")
print(frappe.get_all("Workflow", filters={"document_type": "Journal Entry"}, pluck="name"))

print("\n=== SALES INVOICE: workflows? ===")
print(frappe.get_all("Workflow", filters={"document_type": "Sales Invoice"}, pluck="name"))

print("\n=== COMPANY: opening/cost center fields present ===")
print("has default_cost_center field:", bool(frappe.get_meta("Company").get_field("default_cost_center")))
print("has domain field:", bool(frappe.get_meta("Company").get_field("domain")))
print("domain options:", (frappe.get_meta("Company").get_field("domain").options or "")[:200] if frappe.get_meta("Company").get_field("domain") else "n/a")

print("\n=== FIXED ASSET group children (for Capital Equipment placement) ===")
for a in frappe.get_all("Account", filters={"parent_account": "Fixed Assets - AIG"},
                        fields=["name", "is_group", "account_type"], order_by="lft"):
    print("  ", a)

print("\nDONE-45")
