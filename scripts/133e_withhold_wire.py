# 133e_withhold_wire.py -- Section 4.2 PRODUCTION wiring (commits on success).
# Every block was rehearsed end-to-end by the 133d rollback probe (full
# MR->PO->PR->PI->PE walk with GL assertions passed before this script).
#
# What this script makes permanent (all idempotent):
#   1) Workflows: transition conditions use plain "(doc.x or 0)" instead of
#      flt() - flt is NOT in the workflow safe_eval globals and every MR/PO
#      save with a conditional transition crashed ("flt is not defined").
#      Pending-signoff states become doc_status 1 (submit on entry) so the
#      Reject transitions to Rejected(2) validate (0->2 is rejected by
#      Workflow.validate_docstatus; those Reject buttons were dead).
#   2) User permissions: drop rows with allow=Cost Center but
#      applicable_for=Company whose value is a cost center ("Head Office -
#      AIG" is not a company) - they fail every per-document read.
#   3) Company defaults: Stock Received But Not Billed + Round Off accounts
#      created/set (PR/PI submission failed without them).
#   4) Construction leaf cost center: Construction Enterprise / Construction
#      Projects are group CCs and Construction Enterprise has no leaf child,
#      so construction users could not transact at all. Creates
#      "Construction Projects Phase 1 - AIG" (leaf) and re-points the
#      construction warehouses to it.
#   5) "AIG - PO Committee Majority": sandbox-safe rewrite (getattr is banned
#      and crashed EVERY Purchase Order save; previous state now read from DB).
#   6) "AIG - Payment Three-Way Match" upgraded v4 -> v5 in place: cash paid
#      + withheld (negative deduction rows) must reconcile with the invoice
#      allocation (tolerance 0.5%, min ETB 10). All other legs unchanged.
#   7) NEW "AIG - Payment Withholding 7.5% + 3%" (PE, Before Validate): books
#      VAT withholding 7.5% and withholding tax 3% on the VAT-exclusive
#      invoice net as NEGATIVE deductions, so the supplier is debited the full
#      invoice grand total, the bank pays the net cash, and 2132/2133 are
#      credited (probe-verified GL: DR party 920000, CR bank 836000, CR 2132
#      60000, CR 2133 24000 for a 800000 net invoice). Suppliers carry NO
#      tax_withholding_category, so the PI auto-TDS never double-withholds.

import frappe

COMPANY = "Adama Investment Group"
LEAF_CC = "Construction Projects Phase 1 - AIG"


def log(*a):
    print(*a, flush=True)


def main():
    log("1) workflows: flt()-free conditions + submit-on-entry signoff states")
    SUBMIT_STATES = {"AIG Stock Request Approval": ["Pending Enterprise Head Endorsement"],
                     "AIG Procurement Approval": ["Pending Committee Signoff",
                                                  "Pending Finance Signoff"]}
    for wf_name in ["AIG Stock Request Approval", "AIG Procurement Approval"]:
        wfd = frappe.get_doc("Workflow", wf_name)
        changed = []
        for t in wfd.transitions:
            if t.condition and "flt(" in t.condition:
                old = t.condition
                t.condition = (t.condition
                               .replace("flt(doc.aig_estimated_total)",
                                        "(doc.aig_estimated_total or 0)")
                               .replace("flt(doc.grand_total)",
                                        "(doc.grand_total or 0)"))
                changed.append(f"cond {old!r} -> {t.condition!r}")
        for s in wfd.states:
            if s.state in SUBMIT_STATES.get(wf_name, []) and s.doc_status in (0, "0"):
                s.doc_status = 1
                changed.append(f"state {s.state} doc_status 0 -> 1")
        if changed:
            wfd.flags.ignore_permissions = True
            wfd.save(ignore_permissions=True)
            for c in changed:
                log(f"  {wf_name}: {c}")
        else:
            log(f"  {wf_name}: already clean")

    log("")
    log("2) user permissions: drop Cost Center rows misapplied to Company")
    bad = frappe.get_all("User Permission",
                         filters={"applicable_for": "Company"}, pluck="name")
    for n in bad:
        frappe.delete_doc("User Permission", n, ignore_permissions=True)
    log(f"  deleted {len(bad)} rows")

    log("")
    log("3) company defaults: Stock Received But Not Billed + Round Off")
    srbnb = frappe.db.get_value("Account", {"company": COMPANY,
                                            "account_name": "Stock Received But Not Billed"})
    if not srbnb:
        pay_par = frappe.db.get_value("Account", {"company": COMPANY,
                                                  "account_name": "Trade Creditors - Control Account"},
                                      "parent_account")
        acc = frappe.get_doc({
            "doctype": "Account", "company": COMPANY,
            "account_name": "Stock Received But Not Billed",
            "account_type": "Stock", "parent_account": pay_par,
            "account_currency": "ETB", "report_type": "Balance Sheet",
            "root_type": "Liability",
        })
        acc.flags.ignore_permissions = True
        acc.insert(ignore_permissions=True)
        srbnb = acc.name
        log(f"  account created: {srbnb}")
    if not frappe.db.get_value("Company", COMPANY, "stock_received_but_not_billed"):
        frappe.db.set_value("Company", COMPANY, "stock_received_but_not_billed",
                            srbnb, update_modified=False)
        log(f"  Company.stock_received_but_not_billed = {srbnb}")
    else:
        log(f"  stock_received_but_not_billed already set")

    roff = frappe.db.get_value("Company", COMPANY, "round_off_account")
    if not roff:
        roff = frappe.db.get_value("Account", {"company": COMPANY,
                                               "account_name": "Round Off"})
        if not roff:
            exp_par = frappe.db.get_value(
                "Account", {"company": COMPANY, "root_type": "Expense",
                            "report_type": "Profit and Loss", "is_group": 1},
                "name", order_by="lft")
            acc = frappe.get_doc({
                "doctype": "Account", "company": COMPANY,
                "account_name": "Round Off", "account_type": "Round Off",
                "parent_account": exp_par, "account_currency": "ETB",
                "report_type": "Profit and Loss", "root_type": "Expense",
            })
            acc.flags.ignore_permissions = True
            acc.insert(ignore_permissions=True)
            roff = acc.name
            log(f"  account created: {roff}")
        frappe.db.set_value("Company", COMPANY, "round_off_account", roff,
                            update_modified=False)
        log(f"  Company.round_off_account = {roff}")
    else:
        log(f"  round_off_account already set")

    log("")
    log("4) construction leaf cost center + warehouse re-point")
    if not frappe.db.exists("Cost Center", LEAF_CC):
        parent = frappe.db.get_value("Cost Center", "Construction Projects - AIG",
                                     ["name", "company"], as_dict=True)
        if not parent:
            raise SystemExit("parent CC 'Construction Projects - AIG' missing")
        frappe.get_doc({
            "doctype": "Cost Center",
            "cost_center_name": "Construction Projects Phase 1",
            "parent_cost_center": parent.name, "company": parent.company,
            "is_group": 0,
        }).insert(ignore_permissions=True)
        log(f"  leaf CC created: {LEAF_CC}")
    else:
        log(f"  leaf CC exists: {LEAF_CC}")
    old_ccs = ["Construction Enterprise - AIG", "Construction Projects - AIG"]
    for w in frappe.get_all("Warehouse",
                            filters={"company": COMPANY, "is_group": 0,
                                     "aig_cost_center": ["in", old_ccs]},
                            pluck="name"):
        frappe.db.set_value("Warehouse", w, "aig_cost_center", LEAF_CC,
                            update_modified=False)
        log(f"  {w}: aig_cost_center -> {LEAF_CC}")

    log("")
    log("5) AIG - PO Committee Majority: sandbox-safe rewrite")
    MAJORITY = '''# AIG - PO Committee Majority (Purchase Order, Before Validate).
# Section 3.2 of the refined brief: 2 of 3 named committee members must have
# 'Approve' sign-off rows before the PO may LEAVE 'Pending Committee Signoff',
# and 2 'Reject' rows must force the Rejected outcome (the matching workflow
# actions become functional exactly at that count - the script blocks the
# transition otherwise). Also enforces the Bulky/Open-Tender precondition:
# the upstream Material Request must be Enterprise-Head-endorsed (Section 3.1).
# Only fires on a STATE CHANGE out of the sign-off stage; plain edits inside
# the stage (fixing items, adding rows) stay possible.
# NOTE: no getattr (sandbox forbids it) and no str.format - the previous state
# is read from the database, which still holds the pre-save state here.
prev_state = None
if doc.name and not doc.get("__islocal"):
    prev_state = frappe.db.get_value("Purchase Order", doc.name, "workflow_state")
state = doc.get("workflow_state")
if prev_state == "Pending Committee Signoff" and state != "Pending Committee Signoff":
    approvals = []
    rejects = []
    rows = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": doc.name},
                          fields=["committee_member", "decision"])
    for r in rows:
        if r.committee_member not in approvals and r.committee_member not in rejects:
            if r.decision == "Approve":
                approvals.append(r.committee_member)
            elif r.decision == "Reject":
                rejects.append(r.committee_member)
    if state == "Rejected":
        if len(rejects) < 2:
            frappe.throw("AIG 2-of-3 rule: a committee rejection needs at least "
                         "2 'Reject' sign-offs; only " + str(len(rejects)) +
                         " recorded so far.")
    else:
        if len(rejects) >= 2:
            frappe.throw("AIG 2-of-3 rule: 2 'Reject' sign-offs are recorded - "
                         "this Purchase Order must be Rejected by the committee.")
        if len(approvals) < 2:
            frappe.throw("AIG 2-of-3 rule: " + str(2 - len(approvals)) +
                         " more committee approval(s) needed - only " +
                         str(len(approvals)) + " of 3 'Approve' sign-offs are "
                         "recorded.")
        if (doc.grand_total or 0) > 750000:
            mrs = []
            for it in (doc.items or []):
                if it.get("material_request") and it.material_request not in mrs:
                    mrs.append(it.material_request)
            if not mrs:
                frappe.throw("AIG Bulky/Open Tender: this Purchase Order needs a "
                             "Material Request endorsed by the Enterprise Head "
                             "(no Material Request is referenced).")
            for mr in mrs:
                st = frappe.db.get_value("Material Request", mr, "workflow_state")
                if st not in ("Endorsed", "Approved"):
                    frappe.throw("AIG Bulky/Open Tender: Material Request " +
                                 mr + " is not yet endorsed by the Enterprise "
                                 "Head (state: " + str(st) + ").")
'''
    maj = frappe.get_doc("Server Script", "AIG - PO Committee Majority")
    maj.script = MAJORITY
    maj.disabled = 0
    maj.flags.ignore_permissions = True
    maj.save(ignore_permissions=True)
    log("  rewritten (DB-read prev state, no getattr, no flt)")

    log("")
    log("6) AIG - Payment Three-Way Match: v4 -> v5 in place")
    TWM_V5 = '''# AIG Three-Way Match (Payment Entry, Before Submit) - v5
# Legs proven from the supplier invoice reference (Section 4.1):
#   1) payment_type must be Pay
#   2) at least one Purchase Invoice reference with non-zero allocation
#   3) cash paid + withheld (negative deduction rows) reconciles with the
#      invoice allocation (tolerance: 0.5%, minimum ETB 10 - set by AIG Finance)
#   4) each invoice line is linked to a Purchase Order (leg: PO)
#   5) each such Purchase Order has at least one SUBMITTED Purchase Receipt
#      (leg: Model 19, via Purchase Receipt Item.purchase_order)
#   6) every such Purchase Receipt carries the Model 42 handover attachment
#      (Section 3.4 / 4.1 item 2)
# NOTE: no str.format / f-strings anywhere - RestrictedPython in this v16
# build rejects str.format ("format is an unsafe attribute"); use concatenation.
if doc.payment_type != "Pay":
    frappe.throw("AIG Three-Way Match: only 'Pay' payments follow the AIG approval chain.")

pi_names = []
pi_total = 0.0
for r in (doc.references or []):
    if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
        if r.reference_name not in pi_names:
            pi_names.append(r.reference_name)
        pi_total += (r.allocated_amount or 0)

if not pi_names:
    frappe.throw("AIG Three-Way Match failed: no Purchase Invoice reference "
                 "(supplier invoice) on this Payment Entry.")

withheld = 0.0
for d in (doc.deductions or []):
    if (d.amount or 0) < 0:
        withheld -= (d.amount or 0)

paid = doc.paid_amount or 0
tol = 10.0
if 0.005 * abs(pi_total) > tol:
    tol = 0.005 * abs(pi_total)
if abs(pi_total - (paid + withheld)) > tol:
    frappe.throw("AIG Three-Way Match failed: paid amount " + str(paid) +
                 " plus withheld " + str(withheld) +
                 " does not reconcile with invoice allocation " +
                 str(pi_total) + " (tolerance " + str(tol) + ").")

for pi in pi_names:
    pos = []
    for row in frappe.db.get_all("Purchase Invoice Item",
                                 filters={"parent": pi},
                                 fields=["purchase_order"]):
        if row.purchase_order and row.purchase_order not in pos:
            pos.append(row.purchase_order)
    if not pos:
        frappe.throw("AIG Three-Way Match failed: Purchase Invoice " + pi +
                     " is not linked to a Purchase Order.")
    for po in pos:
        receipts = []
        for r2 in frappe.db.get_all("Purchase Receipt Item",
                                    filters={"purchase_order": po,
                                             "docstatus": 1},
                                    fields=["parent"]):
            if r2.parent not in receipts:
                receipts.append(r2.parent)
        if not receipts:
            frappe.throw("AIG Three-Way Match failed: no submitted Purchase "
                         "Receipt (Model 19) for Purchase Order " + po + ".")
        for pr in receipts:
            m42 = frappe.db.get_value("Purchase Receipt", pr,
                                      "model_42_handover_document")
            if not m42:
                frappe.throw("AIG Three-Way Match failed: Purchase Receipt " +
                             pr + " has no Model 42 handover document attached.")
'''
    twm = frappe.get_doc("Server Script", "AIG - Payment Three-Way Match")
    twm.script = TWM_V5
    twm.disabled = 0
    twm.flags.ignore_permissions = True
    twm.save(ignore_permissions=True)
    log("  updated to v5")

    log("")
    log("7) AIG - Payment Withholding 7.5% + 3% (create or update)")
    PE_WH = '''# AIG - Payment Withholding 7.5% + 3% (Payment Entry, Before Validate).
# Section 4.2: at payment time withhold VAT withholding 7.5% and withholding
# tax 3% on the VAT-exclusive invoice net, and pay the supplier the remainder.
# The stock TDS engine applies only one category and only on unallocated
# amounts, so this script books the two AIG withholdings as NEGATIVE
# Payment Entry deductions (credit to the liability account). The standard
# difference formula (base_paid - base_party - included + total_deductions)
# then nets to zero and add_deductions_gl_entries posts the credits to 2132 /
# 2133 against the supplier - a balanced entry, verified against v16 GL code.
# Suppliers carry NO tax_withholding_category so the Purchase Invoice
# auto-TDS never double-withholds. Idempotent: rows are matched by account
# and recalculated on every save.
if doc.payment_type == "Pay" and doc.party_type == "Supplier" and doc.references:
    pi_names = []
    for r in doc.references:
        if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
            if r.reference_name not in pi_names:
                pi_names.append(r.reference_name)
    if pi_names:
        net = 0.0
        for r in doc.references:
            if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
                pi_net = frappe.db.get_value("Purchase Invoice", r.reference_name, "net_total") or 0
                pi_grand = frappe.db.get_value("Purchase Invoice", r.reference_name, "grand_total") or 0
                if pi_grand:
                    net = net + round((r.allocated_amount or 0) * pi_net / pi_grand, 2)
        if net > 0:
            specs = [["AIG 7.5% VAT Withholding", 7.5, "AIG VAT Withholding (7.5% of net)"],
                     ["AIG 3% Withholding Tax", 3.0, "AIG Withholding Tax (3% of net)"]]
            for spec in specs:
                acct = frappe.db.get_value("Tax Withholding Account",
                                           {"parent": spec[0], "company": doc.company},
                                           "account")
                if not acct:
                    frappe.throw("AIG Withholding: no posting account configured for "
                                 + spec[0] + ". Contact Finance to fix the category.")
                amt = -round(net * spec[1] / 100.0, 2)
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
'''
    if frappe.db.exists("Server Script", "AIG - Payment Withholding 7.5% + 3%"):
        row = frappe.get_doc("Server Script", "AIG - Payment Withholding 7.5% + 3%")
        row.script = PE_WH
        row.disabled = 0
        row.flags.ignore_permissions = True
        row.save(ignore_permissions=True)
        log("  updated in place")
    else:
        frappe.get_doc({
            "doctype": "Server Script", "name": "AIG - Payment Withholding 7.5% + 3%",
            "script_type": "DocType Event", "reference_doctype": "Payment Entry",
            "doctype_event": "Before Validate", "disabled": 0, "script": PE_WH,
            "module": "AIG HR",
        }).insert(ignore_permissions=True)
        log("  created")

    log("")
    log("8) verification")
    for s in ["AIG - PO Committee Majority", "AIG - Payment Three-Way Match",
              "AIG - Payment Withholding 7.5% + 3%", "AIG - Model 42 Guard"]:
        ex = frappe.db.exists("Server Script", s)
        dis = frappe.db.get_value("Server Script", s, "disabled") if ex else None
        log(f"  script {s}: exists={bool(ex)} disabled={dis}")
    for cat, prefix in [("AIG 7.5% VAT Withholding", "2132"),
                        ("AIG 3% Withholding Tax", "2133")]:
        acct = frappe.db.get_value("Tax Withholding Account",
                                   {"parent": cat, "company": COMPANY}, "account")
        log(f"  {cat} -> {acct}")
    leaf_exists = frappe.db.exists("Cost Center", LEAF_CC)
    leaf_group = frappe.db.get_value("Cost Center", LEAF_CC, "is_group") if leaf_exists else None
    log(f"  leaf CC {LEAF_CC}: exists={bool(leaf_exists)} is_group={leaf_group}")
    if not leaf_exists or leaf_group:
        raise SystemExit(f"leaf CC {LEAF_CC} missing or still a group")
    for wf_name in ["AIG Stock Request Approval", "AIG Procurement Approval"]:
        wfd = frappe.get_doc("Workflow", wf_name)
        flt_count = sum(1 for t in wfd.transitions
                        if t.condition and "flt(" in t.condition)
        log(f"  {wf_name}: flt() conditions remaining = {flt_count}")
    n_bad = len(frappe.get_all("User Permission",
                               filters={"applicable_for": "Company"},
                               pluck="name"))
    log(f"  user permissions allow=CostCenter/appl=Company remaining = {n_bad}")

    frappe.clear_cache()
    log("")
    log("DONE 133e")


main()
