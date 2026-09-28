# 80_purge_transactions.py -- Phase 2: clear all demo transactions for
# "Adama Investment Group" so the Chart of Accounts Importer unblocks.
#
# Importer gate (erpnext/accounts/doctype/chart_of_accounts_importer/
# chart_of_accounts_importer.py :: validate_company):
#     if frappe.db.get_all("GL Entry", {"company": company}, "name", limit=1):
#         frappe.throw("Transactions against the Company already exist! ...")
# So: zero GL Entry rows for the company == unblocked. This script cancels and
# deletes every transactional doc, then clears derived ledger tables and
# verifies. Masters (Suppliers, Items except the test item, Warehouses, Users),
# Cost Centers, Accounts, Workflows and Server Scripts are NOT touched
# (Accounts are wiped by the importer itself at import time).
#
# Multi-pass: docs that fail because of dynamic links are retried in later
# passes once the linking docs are gone. Idempotent: safe to re-run.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- inventory
def company_doctypes():
    """All non-child, non-single doctypes (standard + custom field) with a
    'company' Link field pointing at Company."""
    rows = frappe.db.sql(
        """
        select distinct df.parent as dt
        from `tabDocField` df
        join `tabDocType` dt on dt.name = df.parent
        where df.fieldname = 'company' and df.options = 'Company'
          and dt.istable = 0 and dt.issingle = 0
        union
        select distinct cf.dt as dt
        from `tabCustom Field` cf
        join `tabDocType` dt on dt.name = cf.dt
        where cf.fieldname = 'company'
          and dt.istable = 0 and dt.issingle = 0
        """,
        as_dict=1,
    )
    out = []
    for r in rows:
        dt = r["dt"]
        try:
            if frappe.db.table_exists(dt):
                out.append(dt)
        except Exception:
            pass
    return out


def inventory(tag):
    log("=" * 70)
    log(f"INVENTORY {tag}: docs belonging to {COMPANY!r}")
    found = []
    for dt in company_doctypes():
        try:
            cnt = frappe.db.count(dt, {"company": COMPANY})
        except Exception:
            continue
        if cnt:
            found.append((dt, cnt))
    for dt, cnt in sorted(found):
        log(f"  {dt}: {cnt}")
    if not found:
        log("  (none)")
    return dict(found)


# ---------------------------------------------------------------- purge
# Dependency-safe order: linking docs first (Quality Inspection links to Stock
# Entry / Purchase Receipt; Asset Movement links to Asset), then vouchers,
# then orders, then account-linked config docs.
PURGE_ORDER = [
    "Quality Inspection",
    "Repost Item Valuation",
    "Landed Cost Voucher",
    "Payment Entry",
    "Payment Request",
    "Purchase Invoice",
    "Sales Invoice",
    "Journal Entry",
    "Journal Entry Template",
    "Stock Entry",
    "Serial and Batch Bundle",
    "Stock Reconciliation",
    "Serial No",
    "Batch No",
    "Purchase Receipt",
    "Delivery Note",
    "Asset Movement",
    "Asset Depreciation Schedule",
    "Asset",
    "Asset Value Adjustment",
    "Purchase Order",
    "Material Request",
    "Supplier Quotation",
    "Request for Quotation",
    "Budget",
    "Asset Category",   # demo "Dairy Equipment" only (filtered)
    "Item",             # demo "AIG-TEST-MILK-CAN" only (filtered)
    "Bank Account",
    "Item Tax Template",
]

ASSET_CATEGORY_NAMES = {"Dairy Equipment"}
ITEM_NAMES = {"AIG-TEST-MILK-CAN"}


def purge_one(dt, name):
    doc = frappe.get_doc(dt, name)
    if doc.docstatus == 1:
        doc.cancel()
    frappe.delete_doc(dt, name, force=True, ignore_permissions=True, ignore_missing=True)


def purge_targets():
    """Yield (doctype, name) for everything to purge, in dependency order."""
    for dt in PURGE_ORDER:
        if not frappe.db.table_exists(dt):
            continue
        if "company" not in {f.fieldname for f in frappe.get_meta(dt).fields}:
            log(f"  (skip {dt}: no company field)")
            continue
        names = frappe.get_all(dt, filters={"company": COMPANY}, pluck="name")
        if dt == "Asset Category":
            names = [n for n in names if n in ASSET_CATEGORY_NAMES]
        if dt == "Item":
            names = [n for n in names if n in ITEM_NAMES]
        for n in names:
            yield dt, n


log("=" * 70)
log("PURGE")
before = inventory("BEFORE")

pending = list(purge_targets())
log(f"  {len(pending)} document(s) queued")
for pass_no in (1, 2, 3, 4, 5):
    if not pending:
        break
    log(f"  -- pass {pass_no}: {len(pending)} doc(s)")
    failed = []
    for dt, n in pending:
        try:
            purge_one(dt, n)
            log(f"  deleted {dt} {n}")
        except Exception:
            tb = frappe.get_traceback()
            last = tb.strip().splitlines()[-1] if tb else "?"
            log(f"  .. retry later: {dt} {n} ({last[:120]})")
            failed.append((dt, n))
    pending = failed
else:
    if pending:
        log(f"  !! {len(pending)} doc(s) still unpurgeable after 5 passes:")
        for dt, n in pending:
            log(f"     {dt} {n}")

# ------------------------------------------------- derived ledger cleanup
log("=" * 70)
log("DERIVED LEDGER CLEANUP")


def clear_if_present(dt, extra_filters=None):
    if not frappe.db.table_exists(dt):
        return
    filters = {"company": COMPANY}
    if extra_filters:
        filters.update(extra_filters)
    if "company" not in {f.fieldname for f in frappe.get_meta(dt).fields}:
        filters = extra_filters or {}
    cnt = frappe.db.count(dt, filters) if filters else frappe.db.count(dt)
    if cnt:
        frappe.db.delete(dt, filters or None)
        log(f"  cleared {dt}: {cnt} row(s)")
    else:
        log(f"  {dt}: already empty")


clear_if_present("Account Closing Balance")
clear_if_present("GL Entry")
clear_if_present("Payment Ledger Entry")
clear_if_present("Stock Ledger Entry")
clear_if_present("Repost Item Valuation")

# Bin rows are per item-warehouse stock residue; clear for company warehouses.
company_whs = frappe.get_all("Warehouse", filters={"company": COMPANY}, pluck="name")
if company_whs and frappe.db.table_exists("Bin"):
    cnt = frappe.db.count("Bin", {"warehouse": ("in", company_whs)})
    if cnt:
        frappe.db.delete("Bin", {"warehouse": ("in", company_whs)})
        log(f"  cleared Bin: {cnt} row(s)")
    else:
        log("  Bin: already empty")

# Null warehouse-wise stock account refs so they don't dangle after the
# importer deletes accounts (warehouse master itself is kept).
ws = frappe.get_all(
    "Warehouse",
    filters={"company": COMPANY, "account": ("is", "set")},
    pluck="name",
)
for w in ws:
    frappe.db.set_value("Warehouse", w, "account", None)
    log(f"  cleared dangling account ref on Warehouse {w}")

# ---------------------------------------------------------------- verify
log("=" * 70)
log("VERIFICATION")
ok = True
for t in ("GL Entry", "Payment Ledger Entry", "Stock Ledger Entry", "Account Closing Balance"):
    cnt = frappe.db.count(t, {"company": COMPANY})
    status = "OK (empty)" if cnt == 0 else "!! NOT EMPTY"
    if cnt:
        ok = False
    log(f"  {t}: {cnt}  {status}")

after = inventory("AFTER")

ledger_and_purged = set(PURGE_ORDER) | {
    "GL Entry", "Payment Ledger Entry", "Stock Ledger Entry", "Account Closing Balance",
}
KEEP = ledger_and_purged | {
    # masters / config intentionally kept
    "Company", "Account", "Cost Center", "Fiscal Year", "Warehouse", "Supplier",
    "Customer", "Item Group", "User", "Role", "Workflow", "Workflow State",
    "Workflow Action Master", "Server Script", "Client Script", "Custom Field",
    "Property Setter", "Tax Withholding Category", "Purchase Taxes and Charges Template",
    "Sales Taxes and Charges Template", "Item Tax Template", "Item Group",
    "Mode of Payment", "Payment Terms Template", "Print Format", "Department",
    "Designation", "Branch", "Territory", "Item Attribute", "UOM", "Project",
}
leftover = {dt: c for dt, c in after.items() if dt not in KEEP and c > 0}
if leftover:
    ok = False
    log("  !! unexpected leftovers (review before import):")
    for dt, c in sorted(leftover.items()):
        log(f"     {dt}: {c}")

# reassurance: structural config untouched
for dt in ("Account", "Cost Center", "Fiscal Year"):
    cnt = frappe.db.count(dt, {"company": COMPANY})
    log(f"  [kept] {dt}: {cnt}")

log("=" * 70)
if ok:
    log("VERDICT: READY FOR CoA IMPORT")
    log("  GL Entry / Payment Ledger / Stock Ledger / Account Closing Balance")
    log("  are all empty for the company. The importer's validate_company()")
    log("  gate will now pass.")
else:
    log("VERDICT: NOT CLEAN YET -- see '!!' lines above")
