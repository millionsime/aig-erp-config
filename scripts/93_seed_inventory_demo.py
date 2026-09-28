# 93_seed_inventory_demo.py -- Re-seed demo stock after the purge so the
# inventory workflows have something to issue: wire item/expense defaults to
# the NEW CoA, then post Opening-Balance Stock Reconciliations for the two
# stock items. Idempotent (skips if Bin qty already exists). No workflow docs.

import frappe

COMPANY = "Adama Investment Group"

# item -> [(warehouse, qty, valuation)]
SEED = {
    "AIG-INV-FEED": [("Dairy Farm Store - AIG", 500, 40.0)],
    "AIG-PACK": [("Main Store - AIG", 2000, 5.0)],
}
EXPENSE_MAP = {  # new CoA account numbers
    "AIG-INV-FEED": "5103",   # Feed & Veterinary Costs
    "AIG-PACK": "5107",       # Other Direct Costs
}


def log(*a):
    print(*a, flush=True)


def acc(number):
    name = frappe.db.get_value("Account", {"company": COMPANY, "account_number": number}, "name")
    if not name:
        raise RuntimeError(f"Account {number} not found")
    return name


log("STEP 1: item defaults (expense account for Material Issue valuation)")
for item, number in EXPENSE_MAP.items():
    a = acc(number)
    row = frappe.db.exists("Item Default", {"parent": item, "company": COMPANY})
    if row:
        frappe.db.set_value("Item Default", row, "expense_account", a)
        log(f"  {item}: expense -> {a}")
    else:
        frappe.get_doc({
            "doctype": "Item", "name": item,
        }).set("item_defaults", [])
        d = frappe.get_doc("Item", item)
        d.append("item_defaults", {"company": COMPANY, "expense_account": a})
        d.flags.ignore_permissions = True
        d.save()
        log(f"  {item}: created Item Default expense -> {a}")

log("")
log("STEP 2: opening-balance Stock Reconciliations")
CC_MAP = {
    "Dairy Farm Store - AIG": "Dairy Farm - AIG",
    "Main Store - AIG": "Head Office - AIG",
}
count = 0
for item, rows in SEED.items():
    for wh, qty, rate in rows:
        bin_qty = frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty") or 0
        if bin_qty:
            log(f"  {item} @ {wh}: already {bin_qty}, skip")
            continue
        sr = frappe.get_doc({
            "doctype": "Stock Reconciliation",
            "company": COMPANY,
            "purpose": "Opening Stock",
            "aig_cost_center": CC_MAP.get(wh, "Head Office - AIG"),
            "aig_reason_code": "Opening Balance",
            "aig_reason_note": "Demo seed after Phase-2 purge (CoA import). Reversible via cancel.",
            # Opening Stock requires an Asset/Liability difference account;
            # Equity/Retained Earnings is the standard opening-balance offset.
            "expense_account": acc("3002"),
            "items": [{"item_code": item, "warehouse": wh, "qty": qty, "valuation_rate": rate}],
        })
        sr.insert(ignore_permissions=True)
        sr.submit()
        count += 1
        log(f"  submitted {sr.name}: {item} @ {wh} = {qty} @ {rate}")
frappe.db.commit()

log("")
log("STEP 3: verify stock state")
for item, rows in SEED.items():
    for wh, _, _ in rows:
        b = frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh},
                                ["actual_qty", "stock_value"], as_dict=1)
        log(f"  Bin {item} @ {wh}: qty={b.actual_qty if b else 0} value={b.stock_value if b else 0}")
log(f"  Stock Ledger Entries: {frappe.db.count('Stock Ledger Entry', {'company': COMPANY})}")
log(f"  Bins: {frappe.db.count('Bin')}")
gl = frappe.db.count("GL Entry", {"company": COMPANY})
log(f"  GL Entries (stock receipt creates one): {gl}")
