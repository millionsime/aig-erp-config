# 168_accounting_demo_facts.py -- READ-ONLY ground truth for the accounting
# demo-data seeder: FY, accounts, CC tree, warehouses, parties, items, guards.
import frappe

COMPANY = "Adama Investment Group"
ABBR = "AIG"

def log(*a):
    print(*a, flush=True)

log("=== 1. Fiscal years ===")
for fy in frappe.get_all("Fiscal Year",
                         fields=["name", "year_start_date", "year_end_date", "disabled"],
                         order_by="year_start_date desc", limit=5):
    log(" ", fy.name, fy.year_start_date, "->", fy.year_end_date,
        "disabled" if fy.disabled else "active")

log("")
log("=== 2. Company account defaults ===")
comp = frappe.get_doc("Company", COMPANY)
for f in ["default_bank_account", "default_cash_account", "default_receivable_account",
          "default_payable_account", "default_income_account", "default_expense_account",
          "default_round_off_account", "default_inventory_account",
          "unrealized_profit_loss_account", "default_payroll_payable_account"]:
    log(f"  {f}: {getattr(comp, f, None)}")
log("  enable_perpetual_inventory:", getattr(comp, "enable_perpetual_inventory", None))

log("")
log("=== 3. Key accounts (name like patterns) ===")
for pat in ["%", ]:
    pass
for acc in frappe.get_all("Account",
                          filters={"company": COMPANY,
                                   "account_type": ["in", ["Bank", "Cash", "Receivable", "Payable",
                                                           "Cost of Goods Sold", "Stock",
                                                           "Stock Adjustment", "Expense Account",
                                                           "Income Account", "Depreciation",
                                                           "Round Off", "Temporary"]]},
                          fields=["name", "account_number", "account_type", "root_type", "is_group"],
                          order_by="account_number", limit=60):
    log(f"  {acc.account_number or '--'} | {acc.name} | {acc.account_type} | {acc.root_type} | group={acc.is_group}")

log("")
log("=== 4. Cost centers ===")
for cc in frappe.get_all("Cost Center", filters={"company": COMPANY},
                         fields=["name", "is_group", "parent_cost_center"],
                         order_by="lft", limit=40):
    log(f"  {'[G]' if cc.is_group else '    '} {cc.name}  parent={cc.parent_cost_center}")

log("")
log("=== 5. Warehouses ===")
for wh in frappe.get_all("Warehouse", filters={"company": COMPANY},
                         fields=["name", "is_group", "warehouse_name",
                                 "parent_warehouse", "aig_cost_center"],
                         order_by="lft", limit=40):
    log(f"  {'[G]' if wh.is_group else '    '} {wh.name} | cc={wh.aig_cost_center}")

log("")
log("=== 6. Parties ===")
for s in frappe.get_all("Supplier", fields=["name", "supplier_group"], limit=20):
    log("  SUP:", s.name)
for c in frappe.get_all("Customer", fields=["name", "customer_group"], limit=20):
    log("  CUS:", c.name)

log("")
log("=== 7. Items ===")
for it in frappe.get_all("Item", fields=["name", "item_name", "item_group", "is_stock_item", "stock_uom"],
                         limit=30):
    log(f"  {it.name} | {it.item_name} | {it.item_group} | stock={it.is_stock_item} | {it.stock_uom}")

log("")
log("=== 8. Existing transaction counts ===")
for dt in ["Material Request", "Purchase Order", "Purchase Receipt", "Purchase Invoice",
           "Payment Entry", "Sales Invoice", "Stock Entry", "Journal Entry", "Budget"]:
    try:
        log(f"  {dt}: {frappe.db.count(dt)}")
    except Exception as e:
        log(f"  {dt}: ERR {e}")

log("")
log("=== 9. Workflows (which doctypes are workflow-guarded) ===")
for w in frappe.get_all("Workflow", fields=["name", "document_type", "is_active"]):
    log(f"  {w.name} -> {w.document_type} active={w.is_active}")

log("")
log("=== 10. Server scripts that could block inserts (name scan) ===")
for ss in frappe.get_all("Server Script", fields=["name", "reference_doctype", "doctype_event", "disabled"],
                         order_by="reference_doctype"):
    log(f"  [{ss.reference_doctype}] {ss.name} ({ss.doctype_event}){' DISABLED' if ss.disabled else ''}")

log("")
log("=== 11. JE / SI / SE quick insert feasibility ===")
log("  Accounts Receivable:", frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Receivable"}))
log("  default_bank:", comp.default_bank_account)

log("DONE")
