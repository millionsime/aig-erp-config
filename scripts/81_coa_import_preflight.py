# 81_coa_import_preflight.py -- Phase 2 pre-flight for the Chart of Accounts
# Importer. Does a final cleanup pass on demo masters that the transaction
# purge skipped (they have no `company` field), then calls the importer's own
# validate_company() to prove the import gate now passes -- WITHOUT importing.
#
# Cleanup here:
#   * Item "AIG-TEST-MILK-CAN" + its Item Price rows
#   * Asset Category "Dairy Equipment" (its child rows carry the account links)
#   * Item Default child rows for the company (income/expense account defaults
#     would dangle once the importer deletes the accounts)
#   * Item Group child-table rows that reference accounts for the company
#
# Then (read-only):
#   * re-verify the four ledger tables are empty
#   * from erpnext...chart_of_accounts_importer import validate_company
#     validate_company("Adama Investment Group")   -> must not throw
#   * report remaining accounts / templates (informational)

import frappe

COMPANY = "Adama Investment Group"
ASSET_CATEGORY_NAMES = {"Dairy Equipment"}
ITEM_NAMES = {"AIG-TEST-MILK-CAN"}


def log(*a):
    print(*a, flush=True)


log("=" * 70)
log("CLEANUP PASS (company-less demo masters)")

# --- Items (demo test item) + their Item Price rows
for item in list(ITEM_NAMES):
    if not frappe.db.exists("Item", item):
        log(f"  Item {item}: already gone")
        continue
    for ip in frappe.get_all("Item Price", filters={"item_code": item}, pluck="name"):
        frappe.delete_doc("Item Price", ip, force=True, ignore_permissions=True)
        log(f"    deleted Item Price {ip}")
    frappe.delete_doc("Item", item, force=True, ignore_permissions=True)
    log(f"  deleted Item {item}")

# --- Asset Categories (demo)
for cat in ASSET_CATEGORY_NAMES:
    if not frappe.db.exists("Asset Category", cat):
        log(f"  Asset Category {cat}: already gone")
        continue
    frappe.delete_doc("Asset Category", cat, force=True, ignore_permissions=True)
    log(f"  deleted Asset Category {cat}")

# --- child tables of Item / Item Group that carry company-scoped account
#     defaults (Item Default, item-group accounts, deferred-account rows, ...)
for parent_dt in ("Item", "Item Group"):
    meta = frappe.get_meta(parent_dt)
    for fld in meta.fields:
        if fld.fieldtype != "Table" or not fld.options:
            continue
        child = fld.options
        if not frappe.db.table_exists(child):
            continue
        try:
            child_meta = frappe.get_meta(child)
        except Exception:
            continue
        names = {f.fieldname for f in child_meta.fields}
        if "company" not in names:
            continue
        has_account_ref = any(fn.endswith("_account") for fn in names) or "account" in names
        if not has_account_ref:
            continue
        cnt = frappe.db.count(child, {"company": COMPANY, "parenttype": parent_dt})
        if cnt:
            frappe.db.delete(child, {"company": COMPANY, "parenttype": parent_dt})
            log(f"  cleared {cnt} row(s) from {parent_dt}.{fld.fieldname} ({child})")
        else:
            log(f"  {parent_dt}.{fld.fieldname} ({child}): already empty")

# ------------------------------------------------------------------ verify
log("=" * 70)
log("LEDGER VERIFICATION")
clean = True
for t in ("GL Entry", "Payment Ledger Entry", "Stock Ledger Entry", "Account Closing Balance"):
    cnt = frappe.db.count(t, {"company": COMPANY})
    clean = clean and cnt == 0
    log(f"  {t}: {cnt}  {'OK' if cnt == 0 else '!! NOT EMPTY'}")

log("=" * 70)
log("REMAINING (kept on purpose / informational)")
for t in ("Account", "Cost Center", "Fiscal Year", "Warehouse", "Supplier", "Customer",
          "Item", "Item Group", "Budget", "Asset Category", "Purchase Taxes and Charges Template",
          "Sales Taxes and Charges Template", "Tax Withholding Category"):
    try:
        cnt = frappe.db.count(t, {"company": COMPANY})
    except Exception:
        # doctypes without a company field
        if t == "Asset Category":
            cnt = frappe.db.count(t, {"name": ("in", list(ASSET_CATEGORY_NAMES))})
        else:
            cnt = frappe.db.count(t)
    log(f"  {t}: {cnt}")

# ---------------------------------------------------------------- gate test
log("=" * 70)
log("IMPORTER GATE TEST (erpnext validate_company -- read-only)")
try:
    from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import (
        validate_company,
    )
    validate_company(COMPANY)
    log(f"  validate_company({COMPANY!r}) returned without error")
    gate = True
except Exception:
    tb = frappe.get_traceback()
    last = tb.strip().splitlines()[-1] if tb else "?"
    log(f"  !! gate still blocked: {last}")
    gate = False

log("=" * 70)
if clean and gate:
    log("VERDICT: READY -- go to Setup > Chart of Accounts Importer, choose")
    log("  company 'Adama Investment Group', attach the new CoA file and IMPORT.")
    log("  (Run the import as Administrator / Accounts Manager.)")
    log("  After import: re-point Company default accounts, verify Cost Centers,")
    log("  recreate Budgets, then create the new Purchase Orders.")
else:
    log("VERDICT: BLOCKED -- fix the '!!' items above and re-run this script.")
