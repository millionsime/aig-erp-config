# 87_final_touch.py -- Clear default_income_account (re-auto-picked to
# "4101 - Sales - Dairy Products" by Company.on_update/set_default_accounts
# during the repair save) via db.set_value so no on_update can re-fill it.
# Then dump every Company Account-link field + final counts. Read-mostly.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("COMPANY ACCOUNT-LINK FIELDS (BEFORE)")
fields = sorted(
    r[0]
    for r in frappe.db.sql(
        """
        select df.fieldname from `tabDocField` df
        where df.parent='Company' and df.fieldtype='Link' and df.options='Account'
        union
        select cf.fieldname from `tabCustom Field` cf
        where cf.dt='Company' and cf.fieldtype='Link' and cf.options='Account'
        """
    )
)
before = frappe.db.get_value("Company", COMPANY, fields, as_dict=1)
for k in fields:
    if before.get(k):
        log(f"  {k}: {before[k]}")

if before.get("default_income_account"):
    frappe.db.set_value("Company", COMPANY, "default_income_account", None)
    log("  -> cleared default_income_account (per-item income accounts are the right mechanism; AIG to decide a fallback later)")

log("")
log("COMPANY ACCOUNT-LINK FIELDS (AFTER)")
after = frappe.db.get_value("Company", COMPANY, fields, as_dict=1)
for k in fields:
    if after.get(k):
        log(f"  {k}: {after[k]}")

log("")
log("FINAL STATE")
log(f"  Accounts: {frappe.db.count('Account', {'company': COMPANY})}")
log(f"  Cost Centers: {frappe.db.count('Cost Center', {'company': COMPANY})}")
log(f"  Fiscal Years: {frappe.db.count('Fiscal Year', {'company': COMPANY})}")
log(f"  GL Entry: {frappe.db.count('GL Entry', {'company': COMPANY})}")
log(f"  Stock Ledger Entry: {frappe.db.count('Stock Ledger Entry', {'company': COMPANY})}")
log(f"  Payment Ledger Entry: {frappe.db.count('Payment Ledger Entry', {'company': COMPANY})}")
log(f"  Budgets: {frappe.db.count('Budget', {'company': COMPANY})}")
log(f"  Warehouses: {frappe.db.count('Warehouse', {'company': COMPANY})} | Suppliers: {frappe.db.count('Supplier')} | Items: {frappe.db.count('Item')}")
log("")
log("DONE -- instance is ready: budgets next, then new Purchase Orders.")
