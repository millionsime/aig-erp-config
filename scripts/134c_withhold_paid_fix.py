# 134c_withhold_paid_fix.py -- PRODUCTION fix (commits on success).
# The withholding script computed the two deduction rows but left
# paid_amount untouched: a Payment Entry entered at the invoice GROSS total
# then failed with difference != 0 on submit (caught by the 134 acceptance
# run, S15 crash). The script now also enforces the net cash figure:
#   paid_amount = received_amount = sum(PI allocations) - total withheld
# Because the script runs on Before Validate (before PE.validate ->
# set_amounts), the adjusted amounts flow through the standard difference
# computation and the entry balances. Same-currency (ETB) payments only.
import frappe


def log(*a):
    print(*a, flush=True)


PE_WH = '''# AIG - Payment Withholding 7.5% + 3% (Payment Entry, Before Validate).
# Section 4.2: at payment time withhold VAT withholding 7.5% and withholding
# tax 3% on the VAT-exclusive invoice net, and pay the supplier the remainder.
# The stock TDS engine applies only one category and only on unallocated
# amounts, so this script books the two AIG withholdings as NEGATIVE
# Payment Entry deductions (credit to the liability account) and enforces the
# net cash figure: paid = sum(PI allocations) - total withheld. The standard
# difference formula then nets to zero and add_deductions_gl_entries posts
# the credits to 2132 / 2133 against the supplier - a balanced entry,
# probe-verified against v16 GL code (party DR grand, bank CR net,
# 2132 CR 7.5% net, 2133 CR 3% net). Suppliers carry NO
# tax_withholding_category so the Purchase Invoice auto-TDS never
# double-withholds. Idempotent: rows are matched by account and amounts are
# recalculated on every save.
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
'''

row = frappe.get_doc("Server Script", "AIG - Payment Withholding 7.5% + 3%")
row.script = PE_WH
row.disabled = 0
row.flags.ignore_permissions = True
row.save(ignore_permissions=True)
log("  AIG - Payment Withholding 7.5% + 3% now enforces net payment")
frappe.clear_cache()
log("DONE 134c")
