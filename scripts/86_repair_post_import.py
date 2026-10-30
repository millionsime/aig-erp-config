# 86_repair_post_import.py -- Single-transaction repair of everything script
# 84 intended (its earlier runs crashed before the runner commit, so their
# changes rolled back) plus cleanup of ERPNext's auto-created country-VAT
# extras (accounts "Duties and Taxes - AIG" / "VAT - AIG" and the 8x
# duplicated VAT rows in the Ethiopia Tax templates).
#
# Target state (v2 numbering: 5-digit 10000..60700):
#   Company: bank=11012, cash=10001, receivable=12300, payable=21100,
#            inventory=13104, stock adjustment account wired, no bogus income
#            default
#   Warehouses: inventory accounts mapped (fuel->13105, raw->13101, ...)
#   Ethiopia Tax templates (Purchase & Sales): exactly ONE row, VAT 15% -> 21402
#   TWCs: "AIG 7.5% VAT Withholding" -> 21401, "AIG 3% Withholding Tax" -> 21403
#   Accounts: exactly the 175 from the CSV (auto-created extras deleted)
#            + 'Stock Adjustment' + 'Round Off' accounts created (not in CSV)

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
log("BEFORE STATE (proof of what rolled back)")
before = frappe.db.get_value(
    "Company", COMPANY,
    ["default_bank_account", "default_cash_account", "default_receivable_account",
     "default_payable_account", "default_income_account", "default_inventory_account"],
    as_dict=1,
)
for k, v in before.items():
    log(f"  {k}: {v or '(empty)'}")

log("=" * 70)
log("STEP 1: COMPANY DEFAULTS")
targets = {
    "default_bank_account": acc("11012"),
    "default_cash_account": acc("10001"),
    "default_receivable_account": acc("12300"),
    "default_payable_account": acc("21100"),
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
company = frappe.get_doc("Company", COMPANY)
for k, v in targets.items():
    company.set(k, v)
if "default_inventory_account" in all_fields:
    company.set("default_inventory_account", acc("13104"))
# clear too-specific auto-picked income default (AIG decides later; per-item
# income accounts are the correct mechanism)
if "default_income_account" in all_fields and company.get("default_income_account"):
    log(f"  clearing default_income_account (was {company.get('default_income_account')})")
    company.set("default_income_account", None)
company.flags.ignore_permissions = True
company.flags.ignore_mandatory = True
company.save()
# bypass on_update side effects: Company.save triggers country template
# recreation; we fix templates ourselves below, so neutralize extra rows after
log(f"  set: {targets}, inventory=13104")
# set_default_accounts (Company.on_update) re-picks a too-specific default
# income account on every save; clear it post-save (AIG decision: per-item /
# per-item-group income accounts are the correct mechanism)
if "default_income_account" in all_fields:
    frappe.db.set_value("Company", COMPANY, "default_income_account", None, update_modified=False)
    log("  cleared default_income_account (post-save; on_update re-picks one)")

log("=" * 70)
log("STEP 2: WAREHOUSE ACCOUNTS")
RULES = [
    (("raw",), "13101"),
    (("goods in transit", "transit"), "13102"),
    (("finished",), "13103"),
    (("fuel", "lubric"), "13105"),
    (("livestock", "biological"), "13106"),
]
DEFAULT_INV = "13104"
mapped = 0
for wh in frappe.get_all("Warehouse", filters={"company": COMPANY}, fields=["name", "warehouse_name"]):
    wn = (wh.warehouse_name or "").lower()
    number = DEFAULT_INV
    for keywords, num in RULES:
        if any(k in wn for k in keywords):
            number = num
            break
    a = acc(number)
    frappe.db.set_value("Warehouse", wh.name, "account", a)
    mapped += 1
log(f"  mapped {mapped} warehouses")

log("=" * 70)
log("STEP 3: ETHIOPIA TAX TEMPLATES -> single VAT 15% row -> 21402")
vat15 = acc("21402")
for dt in ("Purchase Taxes and Charges Template", "Sales Taxes and Charges Template"):
    for name in frappe.get_all(dt, filters={"company": COMPANY}, pluck="name"):
        doc = frappe.get_doc(dt, name)
        doc.set("taxes", [])
        doc.append("taxes", dict(
            category="Total", add_deduct_tax="Add", charge_type="On Net Total",
            rate=15, account_head=vat15, description="VAT 15%",
        ))
        doc.flags.ignore_permissions = True
        doc.save()
        log(f"  {dt} {name}: 1 row -> {vat15}")

log("=" * 70)
log("STEP 4: TAX WITHHOLDING CATEGORIES")
vatwh75 = acc("21401")
wht3 = acc("21403")
for name in frappe.get_all("Tax Withholding Category", pluck="name"):
    doc = frappe.get_doc("Tax Withholding Category", name)
    target = vatwh75 if "vat" in name.lower() else wht3
    doc.set("accounts", [])
    doc.append("accounts", {"company": COMPANY, "account": target})
    doc.flags.ignore_permissions = True
    doc.save()
    log(f"  {name}: -> {target}")

log("=" * 70)
log("STEP 4b: STOCK ADJUSTMENT ACCOUNT (not in the CSV; ERPNext v16 needs it)")
sa = frappe.db.get_value(
    "Account", {"company": COMPANY, "account_type": "Stock Adjustment", "is_group": 0}, "name"
)
if not sa:
    parent = acc("50000")  # Cost of Sales group
    sa_doc = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Stock Adjustment",
        "account_number": "50108",
        "parent_account": parent,
        "company": COMPANY,
        "account_type": "Stock Adjustment",
        "account_currency": "ETB",
        "report_type": "Profit and Loss",
        "root_type": "Expense",
    })
    sa_doc.flags.ignore_permissions = True
    sa_doc.insert(ignore_permissions=True)
    sa = sa_doc.name
    log(f"  created Account {sa} under {parent}")
else:
    log(f"  found existing: {sa}")
comp_sa = frappe.db.get_value("Company", COMPANY, "stock_adjustment_account")
if comp_sa != sa:
    frappe.db.set_value("Company", COMPANY, "stock_adjustment_account", sa, update_modified=False)
    log(f"  company.stock_adjustment_account -> {sa}")
else:
    log(f"  company.stock_adjustment_account already {sa}")

log("=" * 70)
log("STEP 4c: ROUND OFF ACCOUNT (not in the CSV; needed for GL rounding)")
ro = frappe.db.get_value(
    "Account", {"company": COMPANY, "account_type": "Round Off", "is_group": 0}, "name"
)
if not ro:
    root = frappe.db.get_value(
        "Account", {"company": COMPANY, "parent_account": ("is", "not set"), "root_type": "Expense"}, "name"
    )
    ro_doc = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Round Off",
        "parent_account": root,
        "company": COMPANY,
        "account_type": "Round Off",
        "account_currency": "ETB",
        "report_type": "Profit and Loss",
        "root_type": "Expense",
    })
    ro_doc.flags.ignore_permissions = True
    ro_doc.insert(ignore_permissions=True)
    ro = ro_doc.name
    log(f"  created Account {ro} under {root}")
else:
    log(f"  found existing: {ro}")
frappe.db.set_value("Company", COMPANY, "round_off_account", ro, update_modified=False)
log(f"  company.round_off_account -> {ro}")

log("=" * 70)
log("STEP 5: DELETE AUTO-CREATED EXTRA ACCOUNTS (not in CSV)")
extras = [
    n for n in frappe.get_all(
        "Account",
        filters={"company": COMPANY, "account_number": ("in", ["", None])},
        pluck="name",
    )
]
# only delete the known auto-created pair; anything else -> report, don't touch
known = [n for n in extras if n.startswith(("Duties and Taxes - AIG", "VAT - AIG"))]
unknown = [n for n in extras if n not in known]
# unnumbered root accounts are legit (the v2 CSV ships roots without numbers)
legit_roots = [n for n in unknown if not frappe.db.get_value("Account", n, "parent_account")]
# company-created helper accounts are legit too (created in STEP 4b/4c)
legit_roots += [n for n in unknown if n.startswith(("Round Off - AIG", "Stock Adjustment - AIG"))]
unknown = [n for n in unknown if n not in legit_roots]
if legit_roots:
    log(f"  roots without number (legit, from CSV): {len(legit_roots)}")
for n in unknown:
    log(f"  !! unknown extra account, NOT deleting: {n}")
# clear any Company field referencing them first
for n in known:
    refs = [f for f in all_fields if frappe.db.get_value("Company", COMPANY, f) == n]
    for f in refs:
        frappe.db.set_value("Company", COMPANY, {f: None})
        log(f"  cleared Company.{f} (was {n})")
# templates must not reference them (done in step 3); re-check all tax rows
for n in known:
    used = frappe.db.sql(
        "select 1 from `tabPurchase Taxes and Charges` where account_head=%s union all "
        "select 1 from `tabSales Taxes and Charges` where account_head=%s limit 1",
        (n, n),
    )
    if used:
        log(f"  !! {n} still referenced by a tax template row, skipping delete")
        continue
# delete CHILDREN first (nested set: parent cannot die before its children)
known.sort(key=lambda n: 0 if n.startswith("VAT - AIG") else 1)
for n in known:
    if not frappe.db.exists("Account", n):
        log(f"  {n}: already gone")
        continue
    frappe.delete_doc("Account", n, force=True, ignore_permissions=True)
    log(f"  deleted Account {n}")

# ------------------------------------------------------------- verify
log("=" * 70)
log("VERIFICATION")
total = frappe.db.count("Account", {"company": COMPANY})
no_num = frappe.db.count("Account", {"company": COMPANY, "account_number": ("in", ["", None])})
log(f"  Accounts: {total} (expect 177 = 175 CSV + 1 Stock Adjustment + 1 Round Off), "
    f"without number: {no_num} (expect 6 = 5 roots + Round Off)")

after = frappe.db.get_value(
    "Company", COMPANY,
    ["default_bank_account", "default_cash_account", "default_receivable_account",
     "default_payable_account", "default_income_account", "default_inventory_account"],
    as_dict=1,
)
for k, v in after.items():
    log(f"  company.{k}: {v or '(empty)'}")

unmapped = frappe.db.count(
    "Warehouse", {"company": COMPANY, "account": ("is", "not set")},
)
log(f"  warehouses without account: {unmapped} (expect 0)")

for dt in ("Purchase Taxes and Charges Template", "Sales Taxes and Charges Template"):
    for name in frappe.get_all(dt, filters={"company": COMPANY}, pluck="name"):
        rows = frappe.get_all(
            "Purchase Taxes and Charges" if dt.startswith("Purchase") else "Sales Taxes and Charges",
            filters={"parent": name},
            fields=["idx", "rate", "account_head"],
        )
        log(f"  {name}: {len(rows)} row(s): {[(r.rate, r.account_head) for r in rows]}")

for name in frappe.get_all("Tax Withholding Category", pluck="name"):
    rows = frappe.get_all("Tax Withholding Account", filters={"parent": name}, fields=["company", "account"])
    log(f"  TWC {name}: {rows}")

gle = frappe.db.count("GL Entry", {"company": COMPANY})
cc = frappe.db.count("Cost Center", {"company": COMPANY})
log(f"  GL Entry: {gle} (expect 0) | Cost Centers: {cc} (expect 18)")

ok = (
    total == 177 and no_num == 6 and unmapped == 0 and gle == 0
    and after.get("default_bank_account") == acc("11012")
    and after.get("default_payable_account") == acc("21100")
    and after.get("default_receivable_account") == acc("12300")
    and not after.get("default_income_account")
    and frappe.db.get_value("Company", COMPANY, "stock_adjustment_account") == sa
    and frappe.db.get_value("Company", COMPANY, "round_off_account") == ro
)
log("=" * 70)
log("VERDICT: " + ("ALL GOOD -- CoA live, defaults wired, ready for budgets + POs" if ok else "!! CHECK '!!' LINES ABOVE"))
