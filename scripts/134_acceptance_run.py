# 134_acceptance_run.py -- Section 7 ACCEPTANCE run (commit-on-success).
# Walks every gate of the refined brief as the REAL demo users, asserting the
# exact error messages on the negative cases and the GL math on the positive
# ones. Every document created here is cancelled and deleted at the end, so
# the commit persists nothing (a failure aborts the whole script instead).
#
# Matrix:
#   S1  MR >750k: Procurement-Officer bypass BLOCKED                  (3.1)
#   S2  MR >750k: endorse path -> Endorsed                            (3.1, +)
#   S3  MR <=750k: direct bypass -> Approved                          (3.1, +)
#   S4  PO committee: the member's CLICK is the approval (auto-recorded
#       sign-off, one member on behalf of all)                       (3.2 rev)
#   S5  PO committee: 2 reject rows force Rejected; Reject click works (3.2)
#   S6  PO >750k without endorsed MR -> Forward blocked (Bulky)       (3.3)
#   S7  PO >750k full chain: committee->Corporate->CEO->Approved      (3.3, +)
#   S8  PR without Model 42 -> submit blocked                         (3.4)
#   S9  PI VAT 15% math + auto-TDS inert                              (4.2, +)
#   S10 PE without PI reference -> TWM leg 2 message                   (4.1)
#   S11 PE, PI without PO -> TWM leg 4 message                         (4.1)
#   S12 PE, PO without submitted PR -> TWM leg 5 message               (4.1)
#   S13 PE, PR missing Model 42 -> TWM leg 6 message                   (4.1)
#   S14 PE amount mismatch -> TWM leg 3 message                        (4.1)
#   S15 clean PE through payment chain -> GL 15%/7.5%/3% exact         (4.2, +)
#   S16 CEO-wording audit on custom fields (1.1 re-check)
# Cleanup: cancel+delete every test document (reverse order), supplier, item.

import json
import traceback

import frappe
from frappe.model.workflow import WorkflowPermissionError, apply_workflow
from frappe.utils import flt, nowdate

COMPANY = "Adama Investment Group"
OFFICER = "procurement.agro@aig.local"
HEAD = "head.agro@aig.local"
SUP = "Acceptance Supplier Ltd"
ITEM = "AIG-ACCEPT-ITEM"

RESULTS = []
CREATED = {"MR": [], "PO": [], "PR": [], "PI": [], "PE": [], "CS": []}


def log(*a):
    print(*a, flush=True)


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    log(f"  {'PASS' if ok else 'FAIL'} {case}" + (f" -- {detail}" if detail else ""))


def expect_throw(case, fn, needle):
    try:
        fn()
        record(case, False, "no exception raised")
        return None
    except Exception as e:
        msg = str(e)
        if needle in msg:
            record(case, True, msg.strip().splitlines()[0][:110])
            return e
        record(case, False, f"wrong message: {msg.strip().splitlines()[0][:110]!r} "
                            f"(wanted {needle!r})")
        return e


def as_user(user, fn):
    frappe.set_user(user)
    try:
        return fn()
    finally:
        frappe.set_user("Administrator")


def advance(doc, target, user):
    """Apply the first transition as `user` whose next_state contains target."""
    from frappe.model.workflow import get_transitions

    def run():
        loaded = frappe.get_doc(doc.doctype, doc.name)
        for t in get_transitions(loaded):
            if target in (t.next_state or ""):
                apply_workflow(loaded, t.action)
                return
        raise SystemExit(f"no transition to {target!r} for {doc.doctype} {doc.name}")

    return as_user(user, run)


def make_mr(estimated, endorse):
    def create():
        cc = "Animal Feed Factory - AIG"
        wh = "Animal Feed Plant - AIG"
        mr = frappe.get_doc({
            "doctype": "Material Request", "company": COMPANY,
            "material_request_type": "Purchase", "transaction_date": nowdate(),
            "aig_cost_center": cc, "aig_estimated_total": estimated,
            "items": [{"item_code": ITEM, "qty": 10, "uom": "Nos",
                       "schedule_date": nowdate(), "rate": estimated / 10.0,
                       "warehouse": wh}],
        })
        mr.insert(ignore_permissions=True)
        CREATED["MR"].append(mr.name)
        return mr

    mr = as_user(OFFICER, create)
    if endorse:
        advance(mr, "Pending Enterprise Head Endorsement", OFFICER)
        advance(mr, "Endorsed", HEAD)
        mr.load_from_db()
    return mr


def make_po(mr_name, grand):
    def create():
        cc = "Animal Feed Factory - AIG"
        wh = "Animal Feed Plant - AIG"
        po = frappe.get_doc({
            "doctype": "Purchase Order", "company": COMPANY, "supplier": SUP,
            "transaction_date": nowdate(), "schedule_date": nowdate(),
            "currency": "ETB", "aig_cost_center": cc,
            "items": [{"item_code": ITEM, "qty": 10, "rate": grand / 10.0,
                       "uom": "Nos", "schedule_date": nowdate(),
                       "material_request": mr_name, "warehouse": wh,
                       "cost_center": cc}],
        })
        po.insert(ignore_permissions=True)
        CREATED["PO"].append(po.name)
        return po

    po = as_user(OFFICER, create)
    advance(po, "Pending Committee Signoff", OFFICER)
    return po


def signoffs(po_name, decisions):
    for member, decision in decisions:
        def create():
            frappe.get_doc({
                "doctype": "AIG Committee Signoff", "parent_po": po_name,
                "committee_member": member, "decision": decision,
            }).insert(ignore_permissions=True)
            CREATED["CS"].append(po_name)

        as_user(member, create)


def make_pr(po_name, with_m42=True):
    def create():
        pr = frappe.get_doc({
            "doctype": "Purchase Receipt", "company": COMPANY, "supplier": SUP,
            "posting_date": nowdate(),
            "model_42_handover_document": "accept://m42.pdf" if with_m42 else None,
            "cost_center": "Animal Feed Factory - AIG",
            "items": [{"item_code": ITEM, "qty": 10, "rate": 1000.0,
                       "purchase_order": po_name, "warehouse": "Animal Feed Plant - AIG",
                       "cost_center": "Animal Feed Factory - AIG"}],
        })
        pr.insert(ignore_permissions=True)
        CREATED["PR"].append(pr.name)
        pr.submit()
        return pr

    return as_user(OFFICER, create)


def make_pi(po_name=None):
    def create():
        row = {"item_code": ITEM, "qty": 10, "rate": 1000.0, "uom": "Nos",
               "cost_center": "Animal Feed Factory - AIG"}
        if po_name:
            row["purchase_order"] = po_name
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice", "company": COMPANY, "supplier": SUP,
            "posting_date": nowdate(), "taxes_and_charges": "Ethiopia Tax - AIG",
            "cost_center": "Animal Feed Factory - AIG", "items": [row],
        })
        pi.insert(ignore_permissions=True)
        if pi.taxes_and_charges and not pi.taxes:
            pi.append_taxes_from_master()
            pi.save(ignore_permissions=True)
        pi.submit()
        CREATED["PI"].append(pi.name)
        return pi

    return as_user(OFFICER, create)


def make_pe(pi_name, grand, paid=None):
    comp = frappe.get_doc("Company", COMPANY)
    bank = comp.default_bank_account
    payable = comp.default_payable_account
    paid = grand if paid is None else paid

    def create():
        pe = frappe.get_doc({
            "doctype": "Payment Entry", "company": COMPANY, "payment_type": "Pay",
            "party_type": "Supplier", "party": SUP,
            "paid_from": bank, "paid_to": payable,
            "paid_amount": paid, "received_amount": paid,
            "paid_to_account_currency": "ETB",
            "reference_no": "ACCEPT-REF", "reference_date": nowdate(),
            "cost_center": "Animal Feed Factory - AIG",
            "references": [{"reference_doctype": "Purchase Invoice",
                            "reference_name": pi_name,
                            "total_amount": grand,
                            "outstanding_amount": grand,
                            "allocated_amount": grand}],
        })
        pe.insert(ignore_permissions=True)
        CREATED["PE"].append(pe.name)
        return pe

    return as_user("finance@aig.local", create)


def submit_via_workflow(pe):
    """Submit through the real AIG Payment Approval entry transition (as finance).
    The AIG guard blocks raw submits, so negative cases must walk the chain
    entry exactly like a user would."""

    def run():
        loaded = frappe.get_doc("Payment Entry", pe.name)
        apply_workflow(loaded, "Submit for Deputy Review")

    return as_user("finance@aig.local", run)


def cleanup():
    log("")
    log("cleanup: cancelling + deleting every test document")
    for pe in CREATED["PE"]:
        try:
            frappe.get_doc("Payment Entry", pe).cancel()
        except Exception:
            pass
    for pi in CREATED["PI"]:
        try:
            frappe.get_doc("Purchase Invoice", pi).cancel()
        except Exception:
            pass
    for pr in CREATED["PR"]:
        try:
            frappe.get_doc("Purchase Receipt", pr).cancel()
        except Exception:
            pass
    for po in CREATED["PO"]:
        for cs in frappe.get_all("AIG Committee Signoff",
                                 filters={"parent_po": po}, pluck="name"):
            frappe.delete_doc("AIG Committee Signoff", cs,
                              force=True, ignore_permissions=True)
        try:
            frappe.get_doc("Purchase Order", po).cancel()
        except Exception:
            pass
    for mr in CREATED["MR"]:
        try:
            frappe.get_doc("Material Request", mr).cancel()
        except Exception:
            pass
    for dt, names in [("Payment Entry", CREATED["PE"]),
                      ("Purchase Invoice", CREATED["PI"]),
                      ("Purchase Receipt", CREATED["PR"]),
                      ("Purchase Order", CREATED["PO"]),
                      ("Material Request", CREATED["MR"])]:
        for n in names:
            try:
                frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
            except Exception as e:
                log(f"  !! could not delete {dt} {n}: {e}")
    try:
        frappe.delete_doc("Supplier", SUP, force=True, ignore_permissions=True)
        log("  supplier deleted")
    except Exception as e:
        log(f"  !! supplier delete: {e}")
    try:
        frappe.delete_doc("Item", ITEM, force=True, ignore_permissions=True)
        log("  item deleted")
    except Exception:
        frappe.db.set_value("Item", ITEM, "disabled", 1, update_modified=False)
        log("  item not deletable (cancelled stock rows) -> disabled instead")
    log("  cleanup done")


def main():
    log("setup: supplier + item")
    if frappe.db.exists("Supplier", SUP):
        frappe.delete_doc("Supplier", SUP, force=True, ignore_permissions=True)
    frappe.get_doc({"doctype": "Supplier", "supplier_name": SUP,
                    "supplier_group": frappe.db.get_single_value("Buying Settings",
                                                                 "supplier_group"),
                    "company": COMPANY}).insert(ignore_permissions=True)
    if frappe.db.exists("Item", ITEM):
        frappe.delete_doc("Item", ITEM, force=True, ignore_permissions=True)
    frappe.get_doc({"doctype": "Item", "item_code": ITEM, "item_name": "Accept Item",
                    "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos", "is_stock_item": 1,
                    "is_purchase_item": 1}).insert(ignore_permissions=True)

    log("")
    log("S1) MR 900000: Procurement-Officer direct bypass must be blocked")
    mr = make_mr(900000, endorse=False)
    e = expect_throw(
        "S1 bypass blocked >750k",
        lambda: as_user(OFFICER, lambda: apply_workflow(
            frappe.get_doc("Material Request", mr.name), "Submit Request")),
        "Not a valid Workflow Action")

    log("")
    log("S2) MR 900000: endorse path")
    advance(mr, "Pending Enterprise Head Endorsement", OFFICER)
    advance(mr, "Endorsed", HEAD)
    mr.load_from_db()
    record("S2 endorse path -> Endorsed",
           mr.workflow_state == "Endorsed" and mr.docstatus == 1,
           f"state={mr.workflow_state} docstatus={mr.docstatus}")

    log("")
    log("S3) MR 700000: direct bypass allowed")
    mr2 = make_mr(700000, endorse=False)
    as_user(OFFICER, lambda: apply_workflow(
        frappe.get_doc("Material Request", mr2.name), "Submit Request"))
    mr2.load_from_db()
    record("S3 bypass <=750k -> Approved",
           mr2.workflow_state == "Approved" and mr2.docstatus == 1,
           f"state={mr2.workflow_state}")

    log("")
    log("S4) PO 400000: the member's CLICK is the approval (single-approval "
        "rule, click = decision, 2026-09-27)")
    po = make_po(mr.name, 400000)
    advance(po, "Pending Enterprise Head Approval", "committee1@aig.local")
    rows = frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": po.name},
                          fields=["committee_member", "decision"])
    record("S4 click auto-records the member's Approve row",
           len(rows) == 1 and rows[0].committee_member == "committee1@aig.local"
           and rows[0].decision == "Approve", str(rows))
    advance(po, "Approved", "head.agro@aig.local")
    po.load_from_db()
    record("S4 ONE click -> Approved (member decides for all)",
           po.workflow_state == "Approved" and po.docstatus == 1,
           f"state={po.workflow_state} docstatus={po.docstatus}")

    log("")
    log("S5) PO 400000: 2 reject rows force rejection (reject = row + click, "
        "two members; rule unchanged)")
    po5 = make_po(mr.name, 400000)
    signoffs(po5.name, [("committee1@aig.local", "Reject"),
                        ("committee2@aig.local", "Reject")])
    expect_throw(
        "S5 third member's finalize with 2 rejects blocked",
        lambda: advance(po5, "Pending Enterprise Head Approval",
                        "committee3@aig.local"),
        "must be Rejected by the committee")
    advance(po5, "Rejected", "committee1@aig.local")
    po5.load_from_db()
    record("S5 committee Reject works after 2 rejects",
           po5.workflow_state == "Rejected", f"state={po5.workflow_state}")

    log("")
    log("S6) PO 800000 without endorsed MR: Forward to Tender Committee blocked")
    mr6 = make_mr(800000, endorse=False)  # stays Draft on purpose
    po6 = make_po(mr6.name, 800000)
    signoffs(po6.name, [("committee1@aig.local", "Approve"),
                        ("committee2@aig.local", "Approve")])
    expect_throw(
        "S6 bulky forward without endorsement blocked",
        lambda: advance(po6, "Pending Corporate Approval", "committee1@aig.local"),
        "Bulky/Open Tender")

    log("")
    log("S7) PO 800000 endorsed: full bulky chain to Approved")
    po7 = make_po(mr.name, 800000)  # mr is Endorsed
    signoffs(po7.name, [("committee1@aig.local", "Approve"),
                        ("committee2@aig.local", "Approve")])
    advance(po7, "Pending Corporate Approval", "committee1@aig.local")
    advance(po7, "Pending CEO Approval", "corporate@aig.local")
    advance(po7, "Approved", "ceo@aig.local")
    po7.load_from_db()
    record("S7 bulky chain -> Approved",
           po7.workflow_state == "Approved" and po7.docstatus == 1,
           f"state={po7.workflow_state} docstatus={po7.docstatus}")

    log("")
    log("S8) PR without Model 42 must not submit")
    pr8 = frappe.get_doc({
        "doctype": "Purchase Receipt", "company": COMPANY, "supplier": SUP,
        "posting_date": nowdate(),
        "cost_center": "Animal Feed Factory - AIG",
        "items": [{"item_code": ITEM, "qty": 1, "rate": 1000.0,
                   "purchase_order": po7.name,
                   "warehouse": "Animal Feed Plant - AIG",
                   "cost_center": "Animal Feed Factory - AIG"}],
    })
    pr8.insert(ignore_permissions=True)
    CREATED["PR"].append(pr8.name)
    expect_throw("S8 Model 42 guard blocks submit", pr8.submit, "AIG Model 42")

    log("")
    log("S9) PI VAT 15% + auto-TDS inert")
    pi = make_pi(po7.name)
    net, grand = flt(pi.net_total), flt(pi.grand_total)
    record("S9 VAT grand = net x 1.15", flt(grand, 2) == flt(net * 1.15, 2),
           f"net={net} grand={grand}")
    record("S9 auto-TDS inert (no category/entries)",
           not pi.get("tax_withholding_category") and not (pi.get("tax_withholding_entries") or []))

    log("")
    log("S10) PE without PI reference")
    comp = frappe.get_doc("Company", COMPANY)

    def s10():
        pe = frappe.get_doc({
            "doctype": "Payment Entry", "company": COMPANY, "payment_type": "Pay",
            "party_type": "Supplier", "party": SUP,
            "paid_from": comp.default_bank_account,
            "paid_to": comp.default_payable_account,
            "paid_amount": 1000, "received_amount": 1000,
            "paid_to_account_currency": "ETB",
            "reference_no": "X", "reference_date": nowdate(),
            "cost_center": "Animal Feed Factory - AIG",
        })
        pe.insert(ignore_permissions=True)
        CREATED["PE"].append(pe.name)
        submit_via_workflow(pe)

    expect_throw("S10 no-PI-reference message", s10, "no Purchase Invoice reference")

    log("")
    log("S11) PE against PI that is not linked to a Purchase Order")
    pi11 = make_pi(po_name=None)
    pe11 = make_pe(pi11.name, flt(pi11.grand_total))
    expect_throw("S11 PI-without-PO message", lambda: submit_via_workflow(pe11),
                 "is not linked to a Purchase Order")

    log("")
    log("S12) PE where the PO has no submitted Purchase Receipt")
    # po6 has an endorsed... no: po6's MR is Draft so Forward is blocked. Use a
    # fresh committee-approved <=750k PO (mr2 is Approved so no MR needed).
    po12 = make_po(mr2.name, 300000)
    signoffs(po12.name, [("committee1@aig.local", "Approve"),
                         ("committee2@aig.local", "Approve")])
    advance(po12, "Pending Enterprise Head Approval", "committee1@aig.local")
    advance(po12, "Approved", "head.agro@aig.local")
    pi12 = make_pi(po12.name)
    pe12 = make_pe(pi12.name, flt(pi12.grand_total))
    expect_throw("S12 no-submitted-PR message", lambda: submit_via_workflow(pe12),
                 "no submitted Purchase Receipt")

    log("")
    log("S13) PE where the PR carries no Model 42 (simulated legacy PR)")
    pr_ok = make_pr(po7.name, with_m42=True)
    pi13 = make_pi(po7.name)
    pe13 = make_pe(pi13.name, flt(pi13.grand_total))
    frappe.db.set_value("Purchase Receipt", pr_ok.name,
                        "model_42_handover_document", None, update_modified=False)
    expect_throw("S13 PR-missing-42 message", lambda: submit_via_workflow(pe13),
                 "has no Model 42 handover document")
    frappe.db.set_value("Purchase Receipt", pr_ok.name,
                        "model_42_handover_document", "accept://m42.pdf",
                        update_modified=False)  # restore for S14/S15

    log("")
    log("S14) overpay attempt: raw submit blocked, then neutralized by the "
        "withholder at workflow entry")
    pe14 = make_pe(pi.name, flt(pi.grand_total))
    frappe.db.set_value("Payment Entry", pe14.name,
                        "paid_amount", flt(pi.grand_total) + 100000,
                        update_modified=False)
    expect_throw("S14 raw submit after paid override blocked",
                 lambda: as_user("finance@aig.local", pe14.submit),
                 "only allowed through the AIG Payment Approval workflow")

    def s14_workflow_submit():
        as_user("finance@aig.local", lambda: apply_workflow(
            frappe.get_doc("Payment Entry", pe14.name), "Submit for Deputy Review"))

    s14_workflow_submit()  # must NOT throw: withholder re-derives paid = net
    pe14.load_from_db()
    net14 = flt(pi.net_total)
    expect14 = flt(flt(pi.grand_total) - net14 * 0.075 - net14 * 0.03, 2)
    record("S14 overpay neutralized: paid auto-set to net",
           pe14.docstatus == 1 and flt(pe14.paid_amount, 2) == expect14,
           f"paid={pe14.paid_amount} expected={expect14}")

    log("")
    log("S15) clean payment: own PO->PR->PI chain + approval walk + GL math")
    po15 = make_po(mr2.name, 20000)
    signoffs(po15.name, [("committee1@aig.local", "Approve"),
                         ("committee2@aig.local", "Approve")])
    advance(po15, "Pending Enterprise Head Approval", "committee1@aig.local")
    advance(po15, "Approved", "head.agro@aig.local")
    make_pr(po15.name, with_m42=True)
    pi15 = make_pi(po15.name)
    net15 = flt(pi15.net_total)
    grand15 = flt(pi15.grand_total)
    w1, w2 = flt(net15 * 0.075), flt(net15 * 0.03)
    paid15 = flt(grand15 - w1 - w2)
    pe = make_pe(pi15.name, grand15)  # withholder computes the same split
    pe.load_from_db()
    got = [(d.account.split(" - ")[0], flt(d.amount, 2)) for d in pe.deductions]
    record("S15 withholding rows on PE",
           ("2132", -w1) in got and ("2133", -w2) in got, str(got))
    advance(pe, "Pending Deputy Approval", "finance@aig.local")
    advance(pe, "Pending Corporate Approval", "deputy@aig.local")
    advance(pe, "Pending CEO Approval", "corporate@aig.local")
    advance(pe, "Approved", "ceo@aig.local")
    pe.load_from_db()
    record("S15 payment chain -> Approved",
           pe.workflow_state == "Approved" and pe.docstatus == 1,
           f"state={pe.workflow_state} difference={pe.difference_amount}")
    gl = frappe.get_all("GL Entry", filters={"voucher_no": pe.name},
                        fields=["account", "debit", "credit"])
    pay_prefix = comp.default_payable_account.split(" - ")[0]
    bank_prefix = comp.default_bank_account.split(" - ")[0]

    def gsum(prefix, f):
        return flt(sum(r[f] for r in gl if r["account"].startswith(prefix)))

    record("S15 GL party DR = grand", flt(gsum(pay_prefix, "debit"), 2) == flt(grand15, 2),
           f"got {gsum(pay_prefix, 'debit')} want {grand15}")
    record("S15 GL 2132 CR = 7.5% net", flt(gsum("2132", "credit"), 2) == flt(w1, 2),
           f"got {gsum('2132', 'credit')} want {w1}")
    record("S15 GL 2133 CR = 3% net", flt(gsum("2133", "credit"), 2) == flt(w2, 2),
           f"got {gsum('2133', 'credit')} want {w2}")
    record("S15 GL bank CR = net cash", flt(gsum(bank_prefix, "credit"), 2) == flt(paid15, 2),
           f"got {gsum(bank_prefix, 'credit')} want {paid15}")

    log("")
    log("S16) CEO-wording spot check on custom fields")
    bad = []
    for cf in frappe.get_all("Custom Field",
                             filters={"dt": ["in", ["Material Request",
                                                    "Purchase Order",
                                                    "Payment Entry",
                                                    "Purchase Receipt"]]},
                             fields=["dt", "fieldname", "label"]):
        txt = (cf.label or "").lower()
        if "chief executive" in txt or txt == "ceo":
            bad.append(f"{cf.dt}.{cf.fieldname}: {cf.label}")
    record("S16 no generic CEO labels on custom fields", not bad, str(bad))

    log("")
    fails = [r for r in RESULTS if not r[1]]
    log(f"ACCEPTANCE SUMMARY: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
    for case, ok, detail in RESULTS:
        log(f"  {'PASS' if ok else 'FAIL'} {case}" + (f" -- {detail}" if detail else ""))
    if fails:
        cleanup()
        raise SystemExit(f"{len(fails)} acceptance case(s) FAILED")

    cleanup()

    # final residue check
    residue = []
    for dt, names in [("Payment Entry", CREATED["PE"]),
                      ("Purchase Invoice", CREATED["PI"]),
                      ("Purchase Receipt", CREATED["PR"]),
                      ("Purchase Order", CREATED["PO"]),
                      ("Material Request", CREATED["MR"])]:
        for n in names:
            if frappe.db.exists(dt, n):
                residue.append(f"{dt} {n}")
    if residue:
        raise SystemExit(f"residue left behind: {residue}")
    log("no test residue left - commit persists only the log")


try:
    main()
    log("ACCEPTANCE RUN DONE")
except SystemExit:
    frappe.db.rollback()
    raise
except Exception:
    log("!! ACCEPTANCE RUN CRASHED:")
    log(traceback.format_exc())
    frappe.db.rollback()
    raise
