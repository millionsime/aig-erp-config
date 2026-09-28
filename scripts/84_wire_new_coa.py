# 84_wire_new_coa.py -- Post-import wiring for the new AIG CoA.
#
# The importer's set_default_accounts() auto-detection picked wrong/odd
# defaults (e.g. default_payable_account = Lease Liabilities 2304,
# default_income_account = Sales - Dairy Products 4101). Also:
#   * Purchase/Sales Taxes templates and Tax Withholding Categories lost
#     their account rows (importer deleted rows referencing old accounts)
#   * Warehouse.account was nulled during the transaction purge
# This script re-points everything to the new accounts (fetched by
# account_number, so it is robust to account_name changes), then verifies.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


def acc(number):
    name = frappe.db.get_value("Account", {"company": COMPANY, "account_number": number}, "name")
    if not name:
        raise RuntimeError(f"Account with number {number} not found for {COMPANY}")
    return name


log("=" * 70)
log("COMPANY DEFAULT ACCOUNTS")

targets = {
    "default_bank_account": acc("1110.12"),      # AIG CBE Account (main bank)
    "default_cash_account": acc("1101.01"),      # Petty Cash custodian leaf
    "default_receivable_account": acc("1201"),   # Trade Debtors - Control
    "default_payable_account": acc("2101"),      # Trade Creditors - Control
}

# optional fields that may or may not exist in this version
OPTIONAL = {
    "default_inventory_account": acc("1304"),    # Spare Parts & Consumables
    "round_off_account": frappe.db.get_value(
        "Account", {"company": COMPANY, "name": ("like", "Round Off%")}, "name"
    ),
    "default_deferred_expense_account": None,    # leave for AIG decision
    "default_deferred_revenue_account": None,
}

all_fields = {
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
}

before = frappe.db.get_value("Company", COMPANY, sorted(all_fields), as_dict=1)
log("  BEFORE:")
for k in sorted(all_fields):
    if before.get(k):
        log(f"    {k}: {before[k]}")

# wrong auto-picks that must not survive
if before.get("default_income_account") == acc("4101"):
    updates_income_clear = True
else:
    updates_income_clear = False

company = frappe.get_doc("Company", COMPANY)
for k, v in {**targets, **{k: v for k, v in OPTIONAL.items() if k in all_fields and v}}.items():
    company.set(k, v)
# clear the too-specific auto-picked income default (AIG to decide later;
# per-item / per-item-group income accounts are the correct mechanism here)
if "default_income_account" in all_fields and updates_income_clear:
    company.set("default_income_account", None)
company.flags.ignore_permissions = True
company.flags.ignore_mandatory = True
company.save()
log("  AFTER (set):")
for k, v in {**targets, **{k: v for k, v in OPTIONAL.items() if v}}.items():
    log(f"    {k}: {v}")
if updates_income_clear:
    log("    default_income_account: (cleared -- was auto-set to Sales - Dairy Products 4101)")

# ------------------------------------------------------------- warehouses
log("=" * 70)
log("WAREHOUSE ACCOUNTS")
RULES = [
    (("raw", "feed"), "1301"),
    (("wip", "staging", "receiving", "transit"), "1302"),
    (("finish", "goods"), "1303"),
    (("spare", "consum", "main store"), "1304"),
    (("fuel", "lubric"), "1305"),
    (("livestock", "biological"), "1306"),
]
DEFAULT_INV = "1304"
for wh in frappe.get_all(
    "Warehouse",
    filters={"company": COMPANY},
    fields=["name", "warehouse_name"],
):
    wn = (wh.warehouse_name or "").lower()
    number = DEFAULT_INV
    for keywords, num in RULES:
        if any(k in wn for k in keywords):
            number = num
            break
    a = acc(number)
    cur = frappe.db.get_value("Warehouse", wh.name, "account")
    if cur != a:
        frappe.db.set_value("Warehouse", wh.name, "account", a)
        log(f"  {wh.name}: {cur or '(none)'} -> {a}")
    else:
        log(f"  {wh.name}: already {a}")

# --------------------------------------------------- tax templates / TWC
log("=" * 70)
log("PURCHASE TAXES AND CHARGES TEMPLATES")
vat15 = acc("2131")
vatwh75 = acc("2132")
wht3 = acc("2133")


def row_accounts_ok(doc):
    for r in doc.get("taxes") or []:
        if not frappe.db.exists("Account", {"company": COMPANY, "name": r.account_head}):
            return False
    return True


for name in frappe.get_all("Purchase Taxes and Charges Template", filters={"company": COMPANY}, pluck="name"):
    doc = frappe.get_doc("Purchase Taxes and Charges Template", name)
    log(f"  {name}: current rows:")
    for r in doc.get("taxes") or []:
        log(f"    [{r.idx}] {r.charge_type} {r.rate}% {r.add_deduct_tax} -> {r.account_head} ({r.description})")
    if row_accounts_ok(doc):
        log(f"  {name}: all rows reference existing accounts, left untouched")
        continue
    n = name.lower()
    rows = []
    if "withholding" in n and "vat" in n:
        rows = [
            dict(category="Total", add_deduct_tax="Add", charge_type="On Net Total", rate=15, account_head=vat15, description="VAT 15%"),
            dict(category="Total", add_deduct_tax="Deduct", charge_type="On Net Total", rate=7.5, account_head=vatwh75, description="VAT Withholding 7.5%"),
            dict(category="Total", add_deduct_tax="Deduct", charge_type="On Net Total", rate=3, account_head=wht3, description="Withholding Tax 3%"),
        ]
    elif "withholding" in n:
        rows = [dict(category="Total", add_deduct_tax="Deduct", charge_type="On Net Total", rate=3, account_head=wht3, description="Withholding Tax 3%")]
    elif "vat" in n:
        rows = [dict(category="Total", add_deduct_tax="Add", charge_type="On Net Total", rate=15, account_head=vat15, description="VAT 15%")]
    else:
        # rebuild keeping any still-valid rows; remap dangling VAT/WHT rows by
        # description keywords; drop anything unrecognizable
        for r in doc.get("taxes") or []:
            desc = (r.description or "").lower()
            if frappe.db.exists("Account", {"company": COMPANY, "name": r.account_head}):
                rows.append({k: r.get(k) for k in ("category", "add_deduct", "charge_type", "rate", "account_head", "description")})
            elif "withhold" in desc and "vat" in desc:
                rows.append(dict(category="Total", add_deduct_tax="Deduct", charge_type="On Net Total", rate=7.5, account_head=vatwh75, description="VAT Withholding 7.5%"))
            elif "withhold" in desc:
                rows.append(dict(category="Total", add_deduct_tax="Deduct", charge_type="On Net Total", rate=3, account_head=wht3, description="Withholding Tax 3%"))
            elif "vat" in desc:
                rows.append(dict(category="Total", add_deduct_tax="Add", charge_type="On Net Total", rate=15, account_head=vat15, description="VAT 15%"))
            else:
                log(f"    dropping unrecognizable row [{r.idx}] {r.description} (account gone)")
    if not rows:
        log(f"  {name}: !! nothing to keep, skipped -- needs AIG decision")
        continue
    doc.set("taxes", [])
    for r in rows:
        doc.append("taxes", r)
    doc.flags.ignore_permissions = True
    doc.save()
    log(f"  {name}: rebuilt with {len(rows)} row(s) -> {[r.account_head for r in doc.taxes]}")

log("=" * 70)
log("TAX WITHHOLDING CATEGORIES")
for name in frappe.get_all("Tax Withholding Category", pluck="name"):
    doc = frappe.get_doc("Tax Withholding Category", name)
    doc.set("accounts", [])
    doc.append("accounts", {"company": COMPANY, "account": wht3})
    doc.flags.ignore_permissions = True
    doc.save()
    log(f"  {name}: account row -> {wht3} (rate fields untouched)")

# ------------------------------------------------------------- verify
log("=" * 70)
log("VERIFICATION")
acct_count = frappe.db.count("Account", {"company": COMPANY})
by_root = frappe.get_all(
    "Account", filters={"company": COMPANY},
    fields=["root_type", "count(name) as n"], group_by="root_type",
)
log(f"  Accounts: {acct_count}  by root: " + ", ".join(f"{r.root_type or '?'}={r.n}" for r in by_root))

extra = frappe.get_all(
    "Account",
    filters={"company": COMPANY, "account_number": ("in", ["", None])},
    pluck="name",
)
if extra:
    log(f"  Accounts without number (auto-created by ERPNext): {extra}")

gle = frappe.db.count("GL Entry", {"company": COMPANY})
cc = frappe.db.count("Cost Center", {"company": COMPANY})
fy = frappe.db.count("Fiscal Year", {"company": COMPANY})
log(f"  GL Entry: {gle} (must be 0) | Cost Centers: {cc} | Fiscal Years: {fy}")

bank = frappe.db.get_value("Company", COMPANY, "default_bank_account")
log(f"  Company default_bank_account now: {bank}")

log("=" * 70)
log("WIRING COMPLETE")
log("  Next: recreate Budgets against new expense accounts, then new POs.")
log("  Note: Asset Category 'Dairy Equipment' was deleted in the purge; if")
log("  assets are demoed again, recreate it with rows mapping to 1404/1503/5106.")
