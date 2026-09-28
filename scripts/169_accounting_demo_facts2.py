# 169_accounting_demo_facts2.py -- READ-ONLY: income/expense/equity/temporary
# accounts, Budget + Stock Reconciliation meta, sales-item flags, FY name.
import frappe

COMPANY = "Adama Investment Group"

def log(*a):
    print(*a, flush=True)

log("=== Income leaves ===")
for a in frappe.get_all("Account", filters={"company": COMPANY, "root_type": "Income", "is_group": 0},
                        fields=["name", "account_number"], order_by="account_number", limit=60):
    log(f"  {a.account_number or '--'} | {a.name}")

log("")
log("=== Expense leaves (first 60) ===")
for a in frappe.get_all("Account", filters={"company": COMPANY, "root_type": "Expense", "is_group": 0},
                        fields=["name", "account_number", "account_type"], order_by="account_number", limit=60):
    log(f"  {a.account_number or '--'} | {a.name} | {a.account_type}")

log("")
log("=== Equity leaves ===")
for a in frappe.get_all("Account", filters={"company": COMPANY, "root_type": "Equity", "is_group": 0},
                        fields=["name", "account_number"], order_by="account_number"):
    log(f"  {a.account_number or '--'} | {a.name}")

log("")
log("=== Temporary / round-off / SRD accounts ===")
for a in frappe.get_all("Account", filters={"company": COMPANY,
                                            "name": ["like", "%Temporary%"]},
                        fields=["name"], limit=10):
    log("  ", a.name)
comp = frappe.get_doc("Company", COMPANY)
log("  company.temporary_opening_account:", getattr(comp, "temporary_opening_account", "N/A"))
log("  company.round_off:", getattr(comp, "default_round_off_account", "N/A"))
log("  company.depreciation_expense_account:", getattr(comp, "depreciation_expense_account", "N/A"))
log("  company.disposal_account:", getattr(comp, "disposal_account", "N/A"))
log("  company.capital_work_in_progress_account:", getattr(comp, "capital_work_in_progress_account", "N/A"))

log("")
log("=== Budget meta fieldnames ===")
bm = frappe.get_meta("Budget")
keep = [f.fieldname for f in bm.fields if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Button")]
log(" ", keep)
for cd in bm.get("fields"):
    if cd.fieldtype == "Table":
        tmeta = frappe.get_meta(cd.options)
        tkeep = [f.fieldname for f in tmeta.fields if f.fieldtype not in ("Section Break", "Column Break", "HTML")]
        log(f"  child {cd.options}: {tkeep}")

log("")
log("=== Stock Reconciliation meta ===")
sm = frappe.get_meta("Stock Reconciliation")
keep = [f.fieldname for f in sm.fields if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Button")]
log(" ", keep)

log("")
log("=== Items sales flags ===")
for it in frappe.get_all("Item", fields=["name", "is_sales_item", "is_purchase_item", "is_fixed_asset",
                                          "item_group", "stock_uom", "valuation_rate"],
                         limit=30):
    log(f"  {it.name} | sales={it.is_sales_item} purch={it.is_purchase_item} fixed={it.is_fixed_asset} vr={it.valuation_rate}")

log("")
log("=== Item defaults (expense/income accounts per item) ===")
for d in frappe.get_all("Item Default", fields=["parent", "company", "expense_account", "income_account", "default_warehouse"],
                        filters={"company": COMPANY}, limit=30):
    log(f"  {d.parent}: exp={d.expense_account} inc={d.income_account} wh={d.default_warehouse}")

log("")
log("=== Active FY exact name + companies ===")
for fy in frappe.get_all("Fiscal Year", filters={"disabled": 0}, fields=["name", "year_start_date", "year_end_date"]):
    log("  FY:", fy.name, fy.year_start_date, fy.year_end_date)

log("")
log("=== Customers table empty? UOM check ===")
log("  customers:", frappe.db.count("Customer"))
log("  UOM 'Bag' exists:", frappe.db.exists("UOM", "Bag"))
log("  UOM 'Litre' exists:", frappe.db.exists("UOM", "Litre"))
log("  UOM 'Unit' exists:", frappe.db.exists("UOM", "Unit"))

log("DONE")
