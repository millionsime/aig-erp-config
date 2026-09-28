# 85_coa_health.py -- Inspect CoA state after import + repair tax template /
# party-account residue. Reports accounts that are NOT from the CSV (no
# account_number), dangling references in tax templates / Party Account /
# Mode of Payment Account, and dedupes the 8x duplicated VAT rows.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("=" * 70)
log("ACCOUNT CENSUS")
total = frappe.db.count("Account", {"company": COMPANY})
by_root = frappe.db.sql(
    "select root_type, count(name) n from `tabAccount` where company=%s group by root_type",
    (COMPANY,),
)
log(f"  total: {total}")
for rt, n in by_root:
    log(f"    {rt or '(no root)'}: {n}")

log("  accounts WITHOUT account_number (not from the CSV):")
no_num = frappe.get_all(
    "Account",
    filters={"company": COMPANY, "account_number": ("in", ["", None])},
    fields=["name", "parent_account", "root_type", "account_type", "is_group"],
    order_by="name",
)
for r in no_num:
    log(f"    {r.name} | parent={r.parent_account} | root={r.root_type} | type={r.account_type} | group={r.is_group}")

log("=" * 70)
log("TAX TEMPLATE ROWS")
for dt in ("Purchase Taxes and Charges Template", "Sales Taxes and Charges Template"):
    for name in frappe.get_all(dt, filters={"company": COMPANY}, pluck="name"):
        doc = frappe.get_doc(dt, name)
        log(f"  {dt}: {name} ({len(doc.get('taxes') or [])} rows)")
        for r in doc.get("taxes") or []:
            exists = frappe.db.exists("Account", {"company": COMPANY, "name": r.account_head})
            log(f"    [{r.idx}] {r.charge_type} {r.rate}% {getattr(r, 'add_deduct_tax', '?')} -> {r.account_head} ({r.description}) exists={bool(exists)}")

log("=" * 70)
log("PARTY ACCOUNT / MODE OF PAYMENT ACCOUNT / TWC RESIDUE")
for dt, parent_field in [("Party Account", "parent"), ("Mode of Payment Account", "parent"), ("Tax Withholding Account", "parent")]:
    if not frappe.db.table_exists(dt):
        continue
    rows = frappe.get_all(dt, filters={"company": COMPANY} if "company" in {f.fieldname for f in frappe.get_meta(dt).fields} else {}, fields=["*"])
    log(f"  {dt}: {len(rows)} row(s) for company")
    for r in rows:
        acct = getattr(r, "account", None) or getattr(r, "account_head", None) or getattr(r, "default_account", None)
        ok = frappe.db.exists("Account", {"company": COMPANY, "name": acct}) if acct else None
        log(f"    parent={getattr(r, parent_field, '?')} account={acct} exists={bool(ok)}")

log("=" * 70)
log("GL / LEDGERS")
for t in ("GL Entry", "Payment Ledger Entry", "Stock Ledger Entry"):
    log(f"  {t}: {frappe.db.count(t, {'company': COMPANY})}")
