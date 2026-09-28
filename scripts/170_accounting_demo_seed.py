# 170_accounting_demo_seed.py -- ACCOUNTING DEMO SEEDER (commits on success).
# Fills every cost center with a believable financial story so the CoA,
# Trial Balance, P&L, AR/AP, Cost-Center reports and the /aig-admin dashboard
# have real numbers to show. Safe: rolls back completely if anything fails;
# aborts if a previous seed run is detected (idempotency marker).
#
# Story: July opening balances; August opening stock; Aug-Sep procurement
# across Dairy Farm / Animal Feed Factory / Construction Phase 1 (including
# the 900k bulky tender chain); VAT invoices; three payment legs through the
# full Deputy->Corporate->CEO chain with 7.5%+3% withholding; eight sales
# invoices (three paid, one partial, four open); payroll, utilities, bank
# charges/interest; seven budgets (Warn-only so live demos are never blocked).
import frappe
from frappe.model.workflow import apply_workflow
from collections import defaultdict

COMPANY = "Adama Investment Group"
FY = "2019 EC"
BANK = "1110.12 - AIG CBE Account 1000691900367 - AIG"
PAYABLE = "2101 - Trade Creditors - Control Account - AIG"
RECV = "1201 - Trade Debtors - Control Account - AIG"
CAPITAL = "3001 - Paid-up Capital - AIG"
SALARY = "5201 - Salaries & Wages - AIG"
ELEC = "5302 - Utilities - Electricity - AIG"
BANKCHG = "5505 - Bank Service Charges - AIG"
INTEREST = "4201 - Bank Interest Income - AIG"
STOCK_ADJ = "5099 - Stock Adjustment - AIG"
VAT_TPL = "Ethiopia Tax - AIG"

CC = {
    "feed": "Animal Feed Factory - AIG",
    "dairy": "Dairy Farm - AIG",
    "poultry": "Poultry Farm - AIG",
    "construct": "Construction Projects Phase 1 - AIG",
    "fuel": "Fuel Station - AIG",
    "mall": "City Mall - AIG",
    "parking": "Parking - AIG",
    "cafe": "Cafeteria and Parks - AIG",
    "garage": "Garage - AIG",
    "ho": "Head Office - AIG",
}
WH = {
    "feed": "Animal Feed Plant - AIG",
    "dairy": "Dairy Farm Store - AIG",
    "poultry": "Poultry Farm Store - AIG",
    "construct": "Project Store - AIG",
    "main": "Main Store - AIG",
}
SUP = {
    "dairy": "Ethio Dairy Supplies PLC",
    "agro": "Horizon Agro Inputs PLC",
    "office": "Blue Nile Trade PLC",
    "construct": "Adama Trading PLC",
}
U = {
    "officer_a": "procurement.agro@aig.local",
    "officer_c": "procurement.construction@aig.local",
    "head_a": "head.agro@aig.local",
    "head_c": "head.construction@aig.local",
    "committee": "committee1@aig.local",
    "finance": "finance@aig.local",
    "deputy": "deputy@aig.local",
    "corporate": "corporate@aig.local",
    "ceo": "ceo@aig.local",
}

CREATED = defaultdict(list)


def log(*a):
    print(*a, flush=True)


def as_user(user, fn):
    frappe.set_user(user)
    try:
        return fn()
    finally:
        frappe.set_user("Administrator")


def advance(doctype, name, action, user):
    def run():
        doc = frappe.get_doc(doctype, name)
        apply_workflow(doc, action)
        return doc

    return as_user(user, run)


def guard_already_seeded():
    if frappe.db.exists("Customer", {"customer_name": "Adama Retail Chain PLC"}):
        raise Exception("Seed marker found (demo customers exist) - refusing to double-seed. "
                        "Use the 170 rollback variant or clean manually first.")
    n = frappe.db.count("Journal Entry", {"user_remark": "AIG demo seed"})
    if n:
        raise Exception("Seed marker found (" + str(n) + " seeded JEs) - refusing to double-seed.")


# ---------------------------------------------------------------- masters
def masters():
    log("== masters: customer group, customers, service items")
    if not frappe.db.exists("Customer Group", "AIG Demo Customers"):
        frappe.get_doc({
            "doctype": "Customer Group", "customer_group_name": "AIG Demo Customers",
            "is_group": 0, "parent_customer_group": "All Customer Groups",
        }).insert(ignore_permissions=True)

    customers = {
        "retail": "Adama Retail Chain PLC",
        "hotel": "Bishoftu Hotel & Resort",
        "institute": "Ethiopian Livestock Development Institute",
        "contractor": "Addis Montenegro Construction PLC",
    }
    for key, cname in customers.items():
        frappe.get_doc({
            "doctype": "Customer", "customer_name": cname,
            "customer_type": "Company", "customer_group": "AIG Demo Customers",
            "territory": "Rest Of The World",
        }).insert(ignore_permissions=True)
        CREATED["Customer"].append(cname)
        log("   customer:", cname)

    items = {}
    specs = [
        ("milk", "Raw Milk Bulk Sales", "Litre"),
        ("eggs", "Poultry Eggs (tray)", "Nos"),
        ("diesel", "Diesel Fuel Sales", "Litre"),
        ("hall", "Mall Hall Rental Service", "Unit"),
        ("parking", "Monthly Parking Service", "Unit"),
        ("catering", "Event Catering Service", "Unit"),
        ("fleet", "Fleet Maintenance Service", "Unit"),
    ]
    for key, iname, uom in specs:
        it = frappe.get_doc({
            "doctype": "Item", "item_name": iname, "item_group": "Consumable",
            "stock_uom": uom, "is_stock_item": 0, "is_sales_item": 1,
            "is_purchase_item": 0, "is_fixed_asset": 0,
            "description": "AIG accounting demo service item",
        }).insert(ignore_permissions=True)
        items[key] = it.name
        CREATED["Item"].append(it.name)
        log("   item:", it.name, "=", iname)
    items["feed"] = "AIG-INV-FEED"
    items["pack"] = "AIG-PACK"
    items["laptop"] = "AIG-DEMO-LAPTOP"
    items["chair"] = "AIG-00001"
    items["steel"] = "AIG-STEEL"
    return customers, items


# ---------------------------------------------------------------- stock
def stock_opening():
    log("== stock: opening reconciliation (3 warehouses)")
    # Regular purpose (NOT "Opening Stock"): opening entries demand an
    # Asset/Liability difference account; the regular count accepts the
    # 5099 Stock Adjustment expense and tells a "physical count surplus"
    # story instead. Backdated before all other stock movements.
    purpose = "Stock Reconciliation"
    sm = frappe.get_meta("Stock Reconciliation")
    reason = None
    rf = sm.get_field("aig_reason_code")
    if rf and rf.options:
        opts = [o.strip() for o in rf.options.split("\n") if o.strip() and not o.startswith("#")]
        reason = opts[0] if opts else None

    docs = [
        (WH["feed"], CC["feed"], [
            ("AIG-INV-FEED", 2000, 950.0), ("AIG-PACK", 5000, 12.0)]),
        (WH["poultry"], CC["poultry"], [("AIG-INV-FEED", 300, 950.0)]),
        (WH["main"], CC["ho"], [
            ("AIG-DEMO-LAPTOP", 25, 62000.0), ("AIG-00001", 100, 3500.0)]),
    ]
    for wh, cc, rows in docs:
        sr = frappe.get_doc({
            "doctype": "Stock Reconciliation", "company": COMPANY,
            "purpose": purpose, "posting_date": "2026-08-01",
            "set_warehouse": wh, "aig_cost_center": cc, "cost_center": cc,
            "expense_account": STOCK_ADJ,
            "aig_reason_note": "AIG demo seed: opening stock",
            "items": [{"item_code": i, "warehouse": wh, "qty": q,
                       "valuation_rate": r, "stock_uom": "Nos"} for i, q, r in rows],
        })
        if reason:
            sr.aig_reason_code = reason
        sr.insert(ignore_permissions=True)
        sr.submit()
        CREATED["Stock Reconciliation"].append(sr.name)
        log("   SR:", sr.name, wh, len(rows), "items")


# ------------------------------------------------- procurement chains
def mr_po_chains(items):
    log("== procurement: 4 MR/PO chains through the real workflows")

    def make_mr(user, cc, wh, estimate, item, qty, rate):
        def create():
            mr = frappe.get_doc({
                "doctype": "Material Request", "company": COMPANY,
                "material_request_type": "Purchase", "transaction_date": "2026-08-03",
                "aig_cost_center": cc, "aig_estimated_total": estimate,
                "items": [{"item_code": item, "qty": qty, "uom": "Nos",
                           "schedule_date": "2026-08-10", "rate": rate,
                           "warehouse": wh}],
            }).insert(ignore_permissions=True)
            CREATED["Material Request"].append(mr.name)
            return mr.name

        return as_user(user, create)

    def make_po(user, cc, wh, supplier, item, qty, rate, mr):
        def create():
            row = {"item_code": item, "qty": qty, "rate": rate, "uom": "Nos",
                   "schedule_date": "2026-08-12", "material_request": mr,
                   "warehouse": wh, "cost_center": cc}
            if item == items["steel"]:
                row["expense_account"] = "5107 - Other Direct Costs - AIG"
            po = frappe.get_doc({
                "doctype": "Purchase Order", "company": COMPANY,
                "supplier": supplier, "transaction_date": "2026-08-05",
                "schedule_date": "2026-08-12", "currency": "ETB",
                "aig_cost_center": cc, "items": [row],
            }).insert(ignore_permissions=True)
            CREATED["Purchase Order"].append(po.name)
            return po.name

        return as_user(user, create)

    # PO-1 Dairy: packaging 450,000 (committee path)
    mr1 = make_mr(U["officer_a"], CC["dairy"], WH["dairy"], 450000,
                  items["pack"], 15000, 30.0)
    advance("Material Request", mr1, "Submit Request", U["officer_a"])
    po1 = make_po(U["officer_a"], CC["dairy"], WH["dairy"], SUP["dairy"],
                  items["pack"], 15000, 30.0, mr1)
    advance("Purchase Order", po1, "Submit for Committee Review", U["officer_a"])
    advance("Purchase Order", po1, "Finalize Committee Decision", U["committee"])
    advance("Purchase Order", po1, "Approve", U["head_a"])
    log("   PO-1 (dairy packaging 450k): Approved")

    # PO-2 Animal Feed: laptops 900,000 (bulky tender path)
    mr2 = make_mr(U["officer_a"], CC["feed"], WH["feed"], 900000,
                  items["laptop"], 10, 90000.0)
    advance("Material Request", mr2, "Submit for Endorsement", U["officer_a"])
    advance("Material Request", mr2, "Endorse", U["head_a"])
    po2 = make_po(U["officer_a"], CC["feed"], WH["feed"], SUP["agro"],
                  items["laptop"], 10, 90000.0, mr2)
    advance("Purchase Order", po2, "Submit for Committee Review", U["officer_a"])
    advance("Purchase Order", po2, "Forward to Tender Committee", U["committee"])
    advance("Purchase Order", po2, "Approve", U["corporate"])
    advance("Purchase Order", po2, "Approve", U["ceo"])
    log("   PO-2 (laptops 900k bulky): Approved via Corporate+CEO")

    # PO-3 Animal Feed: small feed additive 15,000 (direct purchase path)
    mr3 = make_mr(U["officer_a"], CC["feed"], WH["feed"], 15000,
                  items["feed"], 500, 30.0)
    advance("Material Request", mr3, "Submit Request", U["officer_a"])
    po3 = make_po(U["officer_a"], CC["feed"], WH["feed"], SUP["agro"],
                  items["feed"], 500, 30.0, mr3)
    advance("Purchase Order", po3, "Submit for Direct Purchase", U["officer_a"])
    advance("Purchase Order", po3, "Finance Sign-off", U["finance"])
    log("   PO-3 (feed additive 15k): Approved direct")

    # PO-4 Construction: steel 600,000 (committee path, construction officer)
    mr4 = make_mr(U["officer_c"], CC["construct"], WH["construct"], 600000,
                  items["steel"], 30, 20000.0)
    advance("Material Request", mr4, "Submit Request", U["officer_c"])
    po4 = make_po(U["officer_c"], CC["construct"], WH["construct"],
                  SUP["construct"], items["steel"], 30, 20000.0, mr4)
    advance("Purchase Order", po4, "Submit for Committee Review", U["officer_c"])
    advance("Purchase Order", po4, "Finalize Committee Decision", U["committee"])
    advance("Purchase Order", po4, "Approve", U["head_c"])
    log("   PO-4 (construction steel 600k): Approved")

    return {"po1": po1, "po2": po2, "po3": po3, "po4": po4}


# ---------------------------------------------------------------- receipts
def receipts(pos, items):
    log("== goods receipts (Model 42 attached)")
    specs = [
        ("pr1", pos["po1"], SUP["dairy"], items["pack"], 15000, 30.0,
         WH["dairy"], CC["dairy"], "2026-08-20"),
        ("pr2", pos["po2"], SUP["agro"], items["laptop"], 10, 90000.0,
         WH["feed"], CC["feed"], "2026-08-25"),
        ("pr3", pos["po3"], SUP["agro"], items["feed"], 500, 30.0,
         WH["feed"], CC["feed"], "2026-08-26"),
    ]
    out = {}
    for key, po, sup, item, qty, rate, wh, cc, date in specs:
        pr = frappe.get_doc({
            "doctype": "Purchase Receipt", "company": COMPANY, "supplier": sup,
            "posting_date": date,
            "model_42_handover_document": "demo://model-42/" + po + ".pdf",
            "cost_center": cc,
            "items": [{"item_code": item, "qty": qty, "rate": rate,
                       "purchase_order": po, "warehouse": wh, "cost_center": cc}],
        }).insert(ignore_permissions=True)
        pr.submit()
        CREATED["Purchase Receipt"].append(pr.name)
        out[key] = pr.name
        log("   ", pr.name, "<-", po)
    return out


# ---------------------------------------------------------------- PIs
def purchase_invoices(pos, items):
    log("== purchase invoices (VAT 15% via template)")
    specs = [
        ("pi1", pos["po1"], SUP["dairy"], items["pack"], 15000, 30.0,
         CC["dairy"], "2026-08-28"),
        ("pi2", pos["po2"], SUP["agro"], items["laptop"], 10, 90000.0,
         CC["feed"], "2026-08-30"),
        ("pi3", pos["po3"], SUP["agro"], items["feed"], 500, 30.0,
         CC["feed"], "2026-09-01"),
    ]
    out = {}
    for key, po, sup, item, qty, rate, cc, date in specs:
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice", "company": COMPANY, "supplier": sup,
            "posting_date": date, "bill_date": date,
            "taxes_and_charges": VAT_TPL, "cost_center": cc,
            "items": [{"item_code": item, "qty": qty, "rate": rate,
                       "purchase_order": po, "cost_center": cc}],
        }).insert(ignore_permissions=True)
        if pi.taxes_and_charges and not pi.taxes:
            pi.append_taxes_from_master()
            pi.save(ignore_permissions=True)
        pi.submit()
        CREATED["Purchase Invoice"].append(pi.name)
        out[key] = pi
        log("   ", pi.name, "<-", po, "grand:", pi.grand_total)

    # unpaid office-supplies PI (no PO) -> AP aging story
    pi4 = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": SUP["office"],
        "posting_date": "2026-09-10", "taxes_and_charges": VAT_TPL,
        "cost_center": CC["ho"],
        "items": [{"item_code": "AIG-00001", "qty": 5, "rate": 1500.0,
                   "expense_account": "5501 - Office Supplies - AIG",
                   "cost_center": CC["ho"]},
                  {"item_code": "AIG-00001", "qty": 20, "rate": 1700.0,
                   "expense_account": "5504 - Printing & Stationery - AIG",
                   "cost_center": CC["ho"]}],
    }).insert(ignore_permissions=True)
    if pi4.taxes_and_charges and not pi4.taxes:
        pi4.append_taxes_from_master()
        pi4.save(ignore_permissions=True)
    pi4.submit()
    CREATED["Purchase Invoice"].append(pi4.name)
    out["pi_office"] = pi4
    log("   ", pi4.name, "(office supplies, stays UNPAID) grand:", pi4.grand_total)

    # unpaid construction steel PI (PO approved, deliberately no receipt/payment)
    pi5 = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY,
        "supplier": SUP["construct"], "posting_date": "2026-09-12",
        "taxes_and_charges": VAT_TPL, "cost_center": CC["construct"],
        "items": [{"item_code": items["steel"], "qty": 30, "rate": 20000.0,
                   "purchase_order": pos["po4"],
                   "expense_account": "5107 - Other Direct Costs - AIG",
                   "cost_center": CC["construct"]}],
    }).insert(ignore_permissions=True)
    if pi5.taxes_and_charges and not pi5.taxes:
        pi5.append_taxes_from_master()
        pi5.save(ignore_permissions=True)
    pi5.submit()
    CREATED["Purchase Invoice"].append(pi5.name)
    out["pi_steel"] = pi5
    log("   ", pi5.name, "(steel, stays UNPAID) grand:", pi5.grand_total)
    return out


# ---------------------------------------------------------------- PEs
def payments(pis):
    log("== payments: full Deputy -> Corporate -> CEO chain with withholding")
    out = {}
    for key, pi_key in [("pe1", "pi1"), ("pe2", "pi2"), ("pe3", "pi3")]:
        pi = pis[pi_key]
        grand = pi.grand_total
        net = pi.net_total
        paid = round(grand - net * 0.105, 2)  # withholder books 7.5% + 3% on net
        cc = pi.cost_center

        def create(pi=pi, grand=grand, paid=paid, cc=cc):
            return frappe.get_doc({
                "doctype": "Payment Entry", "company": COMPANY,
                "payment_type": "Pay", "party_type": "Supplier", "party": pi.supplier,
                "paid_from": BANK, "paid_to": PAYABLE,
                "paid_amount": paid, "received_amount": paid,
                "paid_to_account_currency": "ETB",
                "posting_date": "2026-09-15",
                "reference_no": "DEMO-" + pi.name, "reference_date": "2026-09-15",
                "cost_center": cc,
                "references": [{"reference_doctype": "Purchase Invoice",
                                "reference_name": pi.name,
                                "total_amount": grand,
                                "outstanding_amount": grand,
                                "allocated_amount": grand}],
            }).insert(ignore_permissions=True)

        pe = as_user(U["finance"], create)
        CREATED["Payment Entry"].append(pe.name)
        advance("Payment Entry", pe.name, "Submit for Deputy Review", U["finance"])
        advance("Payment Entry", pe.name, "Approve", U["deputy"])
        advance("Payment Entry", pe.name, "Approve", U["corporate"])
        advance("Payment Entry", pe.name, "Approve", U["ceo"])
        out[key] = pe
        log("   ", pe.name, pi.name, "alloc:", grand, "paid:", paid,
            "(withheld:", round(net * 0.105, 2), ")")
    return out


# ---------------------------------------------------------------- SIs
def sales_invoices(items):
    log("== sales invoices across the enterprises (VAT 15%)")
    specs = [
        ("si_dairy", "hotel", "milk", 8000, 45.0,
         CC["dairy"], "4101 - Sales - Dairy Products - AIG", "2026-08-15", 0),
        ("si_poultry", "retail", "eggs", 4000, 60.0,
         CC["poultry"], "4102 - Sales - Poultry Products - AIG", "2026-08-18", 0),
        ("si_feed", "institute", "feed", 300, 1200.0,
         CC["feed"], "4104 - Sales - Animal Feed - AIG", "2026-09-10", 1),
        ("si_fuel", "retail", "diesel", 20000, 52.0,
         CC["fuel"], "4106 - Sales - Fuel - AIG", "2026-09-14", 0),
        ("si_mall", "hotel", "hall", 1, 120000.0,
         CC["mall"], "4107 - Rental Income - City Mall - AIG", "2026-09-16", 0),
        ("si_parking", "retail", "parking", 15, 3000.0,
         CC["parking"], "4109 - Sales - Parking Services - AIG", "2026-09-18", 0),
        ("si_cafe", "retail", "catering", 1, 180000.0,
         CC["cafe"], "4110 - Sales - Cafeteria & Resort Services - AIG", "2026-09-20", 0),
        ("si_garage", "hotel", "fleet", 1, 95000.0,
         CC["garage"], "4108 - Sales - Garage Services - AIG", "2026-09-22", 0),
    ]
    customers = {c.customer_name: c.customer_name for c in
                 frappe.get_all("Customer", fields=["customer_name"])}
    cmap = {
        "retail": "Adama Retail Chain PLC", "hotel": "Bishoftu Hotel & Resort",
        "institute": "Ethiopian Livestock Development Institute",
    }
    out = {}
    for key, ckey, item, qty, rate, cc, income, date, upd_stock in specs:
        si = frappe.get_doc({
            "doctype": "Sales Invoice", "company": COMPANY,
            "customer": cmap[ckey], "posting_date": date,
            "debit_to": RECV, "update_stock": upd_stock,
            "taxes_and_charges": VAT_TPL, "cost_center": cc,
            "items": [{"item_code": items[item], "qty": qty, "rate": rate,
                       "income_account": income, "cost_center": cc,
                       "warehouse": WH["feed"] if upd_stock else None}],
        }).insert(ignore_permissions=True)
        if si.taxes_and_charges and not si.taxes:
            si.append_taxes_from_master()
            si.save(ignore_permissions=True)
        si.submit()
        CREATED["Sales Invoice"].append(si.name)
        out[key] = si
        log("   ", si.name, cmap[ckey][:24], "grand:", si.grand_total,
            "(PAID later)" if key in ("si_dairy", "si_feed") else
            ("(PART-paid later)" if key == "si_poultry" else "(open)"))
    return out


# ---------------------------------------------------------------- JEs
def journals(sis):
    log("== journals: opening, payroll, utilities, bank, customer receipts")

    def je(remark, date, rows):
        # erpnext recomputes debit/credit from *_in_account_currency *
        # exchange_rate, so raw 'debit' values would be zeroed in validate.
        fixed = []
        for r in rows:
            r = dict(r)
            if "debit" in r:
                r["debit_in_account_currency"] = r.pop("debit")
            if "credit" in r:
                r["credit_in_account_currency"] = r.pop("credit")
            r["exchange_rate"] = 1
            fixed.append(r)
        jv = frappe.get_doc({
            "doctype": "Journal Entry", "company": COMPANY,
            "posting_date": date, "user_remark": remark, "accounts": fixed,
        }).insert(ignore_permissions=True)
        jv.submit()
        CREATED["Journal Entry"].append(jv.name)
        log("   ", jv.name, remark)
        return jv

    je("AIG demo seed: opening balances", "2026-01-01", [
        {"account": BANK, "debit": 12000000, "cost_center": CC["ho"]},
        {"account": CAPITAL, "credit": 12000000, "cost_center": CC["ho"]},
    ])
    je("AIG demo seed: petty cash advance", "2026-08-01", [
        {"account": "1101.01 - Petty Cash - Birhanu Teshome (Custodian) - AIG",
         "debit": 50000, "cost_center": CC["ho"]},
        {"account": BANK, "credit": 50000, "cost_center": CC["ho"]},
    ])
    je("AIG demo seed: August payroll", "2026-08-31", [
        {"account": SALARY, "debit": 150000, "cost_center": CC["ho"]},
        {"account": SALARY, "debit": 120000, "cost_center": CC["feed"]},
        {"account": SALARY, "debit": 80000, "cost_center": CC["dairy"]},
        {"account": SALARY, "debit": 60000, "cost_center": CC["poultry"]},
        {"account": SALARY, "debit": 70000, "cost_center": CC["fuel"]},
        {"account": SALARY, "debit": 90000, "cost_center": CC["mall"]},
        {"account": SALARY, "debit": 130000, "cost_center": CC["construct"]},
        {"account": BANK, "credit": 700000, "cost_center": CC["ho"]},
    ])
    je("AIG demo seed: electricity settled", "2026-09-25", [
        {"account": ELEC, "debit": 30000, "cost_center": CC["mall"]},
        {"account": ELEC, "debit": 25000, "cost_center": CC["feed"]},
        {"account": ELEC, "debit": 30000, "cost_center": CC["ho"]},
        {"account": BANK, "credit": 85000, "cost_center": CC["ho"]},
    ])
    je("AIG demo seed: bank charges", "2026-09-26", [
        {"account": BANKCHG, "debit": 2350, "cost_center": CC["ho"]},
        {"account": BANK, "credit": 2350, "cost_center": CC["ho"]},
    ])
    je("AIG demo seed: interest received", "2026-09-26", [
        {"account": BANK, "debit": 15200, "cost_center": CC["ho"]},
        {"account": INTEREST, "credit": 15200, "cost_center": CC["ho"]},
    ])

    def receipt(remark, date, amount, si_name, customer):
        je(remark, date, [
            {"account": BANK, "debit": amount, "cost_center": CC["ho"]},
            {"account": RECV, "credit": amount, "cost_center": CC["ho"],
             "party_type": "Customer", "party": customer,
             "reference_type": "Sales Invoice", "reference_name": si_name},
        ])

    receipt("AIG demo seed: receipt - dairy milk", "2026-09-05",
            414000, sis["si_dairy"].name, "Bishoftu Hotel & Resort")
    receipt("AIG demo seed: receipt - feed", "2026-09-12",
            414000, sis["si_feed"].name,
            "Ethiopian Livestock Development Institute")
    receipt("AIG demo seed: PART receipt - poultry eggs", "2026-09-14",
            96000, sis["si_poultry"].name, "Adama Retail Chain PLC")


# ---------------------------------------------------------------- budgets
def budgets():
    log("== budgets (all actions WARN - can never block live demos)")
    specs = [
        (CC["feed"], "5103 - Feed & Veterinary Costs - AIG", 2400000),
        (CC["dairy"], "5103 - Feed & Veterinary Costs - AIG", 1800000),
        (CC["poultry"], "5103 - Feed & Veterinary Costs - AIG", 1200000),
        (CC["construct"], "5105 - Sub-contract Costs - AIG", 3000000),
        (CC["fuel"], "5104 - Fuel & Lubricants - COGS - AIG", 2000000),
        (CC["mall"], "5401 - Repairs & Maintenance - Building - AIG", 600000),
        (CC["ho"], SALARY, 2000000),
    ]
    for cc, account, amount in specs:
        frappe.get_doc({
            "doctype": "Budget", "company": COMPANY, "budget_against": "Cost Center",
            "cost_center": cc, "account": account,
            "from_fiscal_year": FY, "to_fiscal_year": FY,
            "budget_amount": amount, "distribution_frequency": "Monthly",
            "applicable_on_material_request": 1,
            "action_if_annual_budget_exceeded_on_mr": "Warn",
            "action_if_accumulated_monthly_budget_exceeded_on_mr": "Warn",
            "applicable_on_purchase_order": 1,
            "action_if_annual_budget_exceeded_on_po": "Warn",
            "action_if_accumulated_monthly_budget_exceeded_on_po": "Warn",
            "applicable_on_booking_actual_expenses": 1,
            "action_if_annual_budget_exceeded": "Warn",
            "action_if_accumulated_monthly_budget_exceeded": "Warn",
        }).insert(ignore_permissions=True)
        log("   budget:", cc, "->", account.split(" - ")[0], amount)


# ---------------------------------------------------------------- reports
def reports():
    log("")
    log("================ ACCOUNTING PICTURE (live GL) ================")
    log("")
    log("--- Debit/Credit per cost center ---")
    for r in frappe.db.sql("""
        SELECT cost_center, SUM(debit) d, SUM(credit) c
        FROM `tabGL Entry` WHERE company=%s AND is_cancelled=0 AND cost_center IS NOT NULL
        GROUP BY cost_center ORDER BY d DESC""", (COMPANY,), as_dict=1):
        log(f"  {r.cost_center:42s} Dr {r.d:>14,.0f}  Cr {r.c:>14,.0f}")

    log("")
    log("--- Expense by cost center (P&L view) ---")
    for r in frappe.db.sql("""
        SELECT gle.cost_center cc, SUM(gle.debit - gle.credit) amt
        FROM `tabGL Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company=%s AND gle.is_cancelled=0 AND a.root_type='Expense'
        GROUP BY gle.cost_center HAVING amt > 0 ORDER BY amt DESC""", (COMPANY,), as_dict=1):
        log(f"  {r.cc:42s} {r.amt:>14,.0f}")

    log("")
    log("--- Income by cost center (P&L view) ---")
    for r in frappe.db.sql("""
        SELECT gle.cost_center cc, SUM(gle.credit - gle.debit) amt
        FROM `tabGL Entry` gle
        JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company=%s AND gle.is_cancelled=0 AND a.root_type='Income'
        GROUP BY gle.cost_center HAVING amt > 0 ORDER BY amt DESC""", (COMPANY,), as_dict=1):
        log(f"  {r.cc:42s} {r.amt:>14,.0f}")

    log("")
    log("--- Key balances ---")
    keys = [(BANK, "Bank 1110.12"),
            ("1101.01 - Petty Cash - Birhanu Teshome (Custodian) - AIG", "Petty cash"),
            (RECV, "Trade debtors 1201"),
            (PAYABLE, "Trade creditors 2101"),
            ("2131 - VAT Payable 15% - AIG", "VAT payable 2131"),
            ("2132 - VAT Withholding Payable 7.5% - AIG", "VAT-WH 2132"),
            ("1304 - Spare Parts & Consumables - AIG", "Inventory 1304")]
    for acc, label in keys:
        bal = frappe.db.sql("""
            SELECT SUM(debit - credit) b FROM `tabGL Entry`
            WHERE company=%s AND is_cancelled=0 AND account=%s""",
            (COMPANY, acc))[0][0] or 0
        log(f"  {label:24s} {bal:>14,.2f}")

    log("")
    log("--- Open AR (Sales Invoice outstanding) ---")
    for r in frappe.db.sql("""
        SELECT name, customer, grand_total, outstanding_amount, posting_date
        FROM `tabSales Invoice` WHERE company=%s AND docstatus=1
        AND outstanding_amount > 0 ORDER BY outstanding_amount DESC""",
        (COMPANY,), as_dict=1):
        log(f"  {r.name} {r.customer[:32]:32s} {r.outstanding_amount:>12,.0f} ({r.posting_date})")

    log("")
    log("--- Open AP (Purchase Invoice outstanding) ---")
    for r in frappe.db.sql("""
        SELECT name, supplier, grand_total, outstanding_amount, posting_date
        FROM `tabPurchase Invoice` WHERE company=%s AND docstatus=1
        AND outstanding_amount > 0 ORDER BY outstanding_amount DESC""",
        (COMPANY,), as_dict=1):
        log(f"  {r.name} {r.supplier[:32]:32s} {r.outstanding_amount:>12,.0f} ({r.posting_date})")

    log("")
    try:
        from frappe.desk.query_report import get_report_content  # noqa
    except Exception:
        pass
    tb_bal = frappe.db.sql("""
        SELECT SUM(debit) - SUM(credit) FROM `tabGL Entry`
        WHERE company=%s AND is_cancelled=0""", (COMPANY,))[0][0] or 0
    log(f"--- TRIAL BALANCE DIFFERENCE (must be 0): {tb_bal:,.2f}")
    log("===============================================================")


def main():
    guard_already_seeded()
    customers, items = masters()
    stock_opening()
    pos = mr_po_chains(items)
    receipts(pos, items)
    pis = purchase_invoices(pos, items)
    payments(pis)
    sis = sales_invoices(items)
    journals(sis)
    budgets()
    reports()
    log("")
    log("SEED COMPLETE - created:",
        {k: len(v) for k, v in CREATED.items()})


main()
log("OK:170")
