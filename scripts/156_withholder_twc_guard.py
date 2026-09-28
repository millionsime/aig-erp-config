# 156_withholder_twc_guard.py -- P0 bomb #1 (commits on success).
# The AIG withholder books VAT-WH 7.5% + WHT 3% as negative PE deductions.
# If a Supplier ever carries a Tax Withholding Category, ERPNext's auto-TDS
# engine would withhold AGAIN on the Purchase Invoice - the same money twice.
# Nothing prevents that today. This patch adds the guard: any PE referencing
# a PI whose supplier has a TWC is thrown back with a precise message.
# Sandbox-safe: no getattr, no flt, no str.format. Idempotent (whole-script
# replace, same mechanism as 133e/146/148).
import frappe


def log(*a):
    print(*a, flush=True)


WITHHOLDER = '''# AIG - Payment Withholding 7.5% + 3% (Payment Entry, Before Validate).
# Section 4.2: at payment time withhold VAT withholding 7.5% and withholding
# tax 3% on the VAT-exclusive invoice net, and pay the supplier the remainder.
# The stock TDS engine applies only one category and only on unallocated
# amounts, so this script books the two AIG withholdings as NEGATIVE
# Payment Entry deductions (credit to the liability account) and enforces the
# net cash figure: paid = sum(PI allocations) - total withheld. The standard
# difference formula then nets to zero and add_deductions_gl_entries posts
# the credits to 2132 / 2133 against the supplier - a balanced entry,
# probe-verified against v16 GL code (party DR grand, bank CR net,
# 2132 CR 7.5% net, 2133 CR 3% net). Suppliers must carry NO
# tax_withholding_category (the Purchase Invoice auto-TDS would otherwise
# double-withhold) - DOUBLE-WITHHOLDING GUARD below throws if one does.
# Idempotent: rows are matched by account and amounts are recalculated on
# every save.
if doc.payment_type == "Pay" and doc.party_type == "Supplier" and doc.references:
    pi_names = []
    for r in doc.references:
        if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
            if r.reference_name not in pi_names:
                pi_names.append(r.reference_name)
    if pi_names:
        net = 0.0
        alloc = 0.0
        for r in doc.references:
            if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
                alloc = alloc + (r.allocated_amount or 0)
                pi_net = frappe.db.get_value("Purchase Invoice", r.reference_name, "net_total") or 0
                pi_grand = frappe.db.get_value("Purchase Invoice", r.reference_name, "grand_total") or 0
                if pi_grand:
                    net = net + round((r.allocated_amount or 0) * pi_net / pi_grand, 2)
        if net > 0:
            specs = [["AIG 7.5% VAT Withholding", 7.5, "AIG VAT Withholding (7.5% of net)"],
                     ["AIG 3% Withholding Tax", 3.0, "AIG Withholding Tax (3% of net)"]]
            w_total = 0.0
            for spec in specs:
                acct = frappe.db.get_value("Tax Withholding Account",
                                           {"parent": spec[0], "company": doc.company},
                                           "account")
                if not acct:
                    frappe.throw("AIG Withholding: no posting account configured for "
                                 + spec[0] + ". Contact Finance to fix the category.")
                amt = -round(net * spec[1] / 100.0, 2)
                w_total = w_total - amt
                found = None
                for d in (doc.deductions or []):
                    if d.account == acct:
                        found = d
                        break
                if found:
                    found.amount = amt
                else:
                    doc.append("deductions", {"account": acct,
                                              "description": spec[2],
                                              "amount": amt,
                                              "cost_center": doc.cost_center})
            target = round(alloc - w_total, 2)
            doc.paid_amount = target
            doc.received_amount = target
        for pn in pi_names:
            sup = frappe.db.get_value("Purchase Invoice", pn, "supplier")
            twc = frappe.db.get_value("Supplier", sup, "tax_withholding_category") if sup else None
            if twc:
                frappe.throw("AIG double-withholding guard: supplier " + str(sup) +
                             " carries a Tax Withholding Category (" + str(twc) +
                             "), so the Purchase Invoice " + str(pn) +
                             " would withhold automatically AND this payment "
                             "withholds again. Remove the category from the "
                             "supplier (AIG withholds at payment time only).")
'''

row = frappe.get_doc("Server Script", "AIG - Payment Withholding 7.5% + 3%")
row.script = WITHHOLDER
row.disabled = 0
row.flags.ignore_permissions = True
row.save(ignore_permissions=True)
log("AIG - Payment Withholding 7.5% + 3%: double-withholding guard installed")
frappe.clear_cache()

log("")
log("verify: PE against a PI whose supplier carries a TWC must throw")
SUP = "TWC Guard Probe Ltd"
ITEM = "AIG-ACCEPT-ITEM"
COMPANY = "Adama Investment Group"
CC = "Animal Feed Factory - AIG"
CREATED = {"PI": None}
try:
    if frappe.db.exists("Supplier", SUP):
        frappe.delete_doc("Supplier", SUP, force=True, ignore_permissions=True)
    frappe.get_doc({"doctype": "Supplier", "supplier_name": SUP,
                    "supplier_group": frappe.db.get_single_value(
                        "Buying Settings", "supplier_group"),
                    "company": COMPANY,
                    "tax_withholding_category": "AIG 3% Withholding Tax"
                    }).insert(ignore_permissions=True)
    if not frappe.db.exists("Item", ITEM):
        frappe.get_doc({"doctype": "Item", "item_code": ITEM,
                        "item_name": "Accept Item",
                        "item_group": frappe.db.get_value(
                            "Item Group", {"is_group": 0}, "name"),
                        "stock_uom": "Nos", "is_stock_item": 1,
                        "is_purchase_item": 1}).insert(ignore_permissions=True)
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": SUP,
        "posting_date": frappe.utils.nowdate(),
        "taxes_and_charges": "Ethiopia Tax - AIG", "cost_center": CC,
        "items": [{"item_code": ITEM, "qty": 1, "rate": 10000.0,
                   "uom": "Nos", "cost_center": CC}],
    })
    pi.insert(ignore_permissions=True)
    if pi.taxes_and_charges and not pi.taxes:
        pi.append_taxes_from_master()
        pi.save(ignore_permissions=True)
    pi.submit()
    CREATED["PI"] = pi.name
    comp = frappe.get_doc("Company", COMPANY)
    pe = frappe.get_doc({
        "doctype": "Payment Entry", "company": COMPANY,
        "payment_type": "Pay", "party_type": "Supplier", "party": SUP,
        "paid_from": comp.default_bank_account,
        "paid_to": comp.default_payable_account,
        "paid_amount": 11500, "received_amount": 11500,
        "paid_to_account_currency": "ETB",
        "reference_no": "TWC-GUARD", "reference_date": frappe.utils.nowdate(),
        "cost_center": CC,
        "references": [{"reference_doctype": "Purchase Invoice",
                        "reference_name": pi.name,
                        "total_amount": pi.grand_total,
                        "outstanding_amount": pi.grand_total,
                        "allocated_amount": pi.grand_total}],
    })
    thrown = ""
    try:
        pe.insert(ignore_permissions=True)
    except Exception as e:
        thrown = str(e)
    if "double-withholding guard" in thrown:
        log(f"  PASS guard threw: {thrown.strip().splitlines()[0][:100]}")
    else:
        log(f"  FAIL expected guard throw, got: {thrown!r}")
        raise SystemExit("TWC guard verification FAILED")
finally:
    if CREATED["PI"]:
        try:
            if frappe.db.get_value("Purchase Invoice", CREATED["PI"],
                                   "docstatus") == 1:
                frappe.get_doc("Purchase Invoice",
                               CREATED["PI"]).cancel()
            frappe.delete_doc("Purchase Invoice", CREATED["PI"],
                              force=True, ignore_permissions=True)
        except Exception as e:
            log(f"  !! PI cleanup: {e}")
    try:
        frappe.delete_doc("Supplier", SUP, force=True,
                          ignore_permissions=True)
    except Exception as e:
        log(f"  !! supplier cleanup: {e}")
log("no residue - commit persists only the script + log")
log("DONE 156")
