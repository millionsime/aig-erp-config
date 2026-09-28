# 133_model42_and_threeway_v4.py -- Refined brief Sections 3.4 + 4.1 + 4.2:
#   A) Model 42 handover document on Purchase Receipt: custom Attach field
#      "model_42_handover_document" (label per brief), mandatory at SUBMIT via
#      a Server Script guard (raw submit also blocked, consistent with PO/PE
#      guards). Standard Purchase Receipt has no workflow here; 'mandatory
#      on submit' via script is the brief-sanctioned mechanism.
#   B) "AIG - Payment Three-Way Match" upgraded v4 IN PLACE:
#      - legs kept from v3 (invoice refs, paid vs allocation tolerance, PO on
#        every invoice line, submitted Purchase Receipt per PO) with all error
#        messages REWRITTEN WITHOUT str.format (RestrictedPython: "format is
#        an unsafe attribute" would replace the intended message with a
#        SyntaxError - caught live in script 113).
#      - NEW leg: every Purchase Receipt on the chain must carry the Model 42
#        attachment (Section 4.1 item 2).
#   C) Withholding wiring audit (Section 4.2): confirm the two TWCs point at
#      the right liability accounts (2132 VAT WH 7.5%, 2133 WHT 3%) and check
#      how v16 Payment Entry picks the TWC (custom field present?).

import frappe

PR = "Purchase Receipt"
M42 = "model_42_handover_document"


def log(*a):
    print(*a, flush=True)


log("A) Model 42 attach field on Purchase Receipt")
if frappe.db.exists("Custom Field", f"{PR}-{M42}"):
    log("  exists")
else:
    frappe.get_doc({
        "doctype": "Custom Field", "dt": PR, "fieldname": M42,
        "fieldtype": "Attach", "label": "Model 42 - Signed Handover Document "
                                        "(required before submission)",
        "description": "Attach the signed Model 42 handover document. The "
                       "receipt cannot be submitted without it, and supplier "
                       "payment is blocked until it is present.",
        "insert_after": "lr_no",
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("A2) submission guard (mandatory-on-submit, no workflow on this doctype)")
M42_GUARD = """# AIG - Model 42 Handover Guard (Purchase Receipt, Before Submit).
# Section 3.4: a Purchase Receipt (Model 19) cannot be submitted without the
# signed Model 42 handover document attached. Also blocks the payment leg
# upstream: the Three-Way Match on Payment Entry re-checks this attachment.
if not doc.get("model_42_handover_document"):
    frappe.throw("AIG Model 42: attach the signed handover document "
                 "(field 'Model 42 - Signed Handover Document') before "
                 "submitting this Purchase Receipt.")
"""
if frappe.db.exists("Server Script", "AIG - Model 42 Guard"):
    row = frappe.get_doc("Server Script", "AIG - Model 42 Guard")
    row.script = M42_GUARD
    row.disabled = 0
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  AIG - Model 42 Guard updated")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - Model 42 Guard",
        "script_type": "DocType Event", "reference_doctype": PR,
        "doctype_event": "Before Submit", "disabled": 0, "script": M42_GUARD,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  AIG - Model 42 Guard created")

log("")
log("B) Three-Way Match v4 (in place, sandbox-safe messages + Model 42 leg)")
TWM = """# AIG Three-Way Match (Payment Entry, Before Submit) - v4
# Legs proven from the supplier invoice reference (Section 4.1):
#   1) payment_type must be Pay
#   2) at least one Purchase Invoice reference with non-zero allocation
#   3) paid_amount reconciles with the invoice allocation (tolerance: 0.5%,
#      minimum ETB 10 - set by AIG Finance for rounding)
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

paid = doc.paid_amount or 0
tol = 10.0
if 0.005 * abs(pi_total) > tol:
    tol = 0.005 * abs(pi_total)
if abs(pi_total - paid) > tol:
    frappe.throw("AIG Three-Way Match failed: paid amount " + str(paid) +
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
"""
if frappe.db.exists("Server Script", "AIG - Payment Three-Way Match"):
    row = frappe.get_doc("Server Script", "AIG - Payment Three-Way Match")
    row.script = TWM
    row.disabled = 0
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  AIG - Payment Three-Way Match updated to v4")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": "AIG - Payment Three-Way Match",
        "script_type": "DocType Event", "reference_doctype": "Payment Entry",
        "doctype_event": "Before Submit", "disabled": 0, "script": TWM,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  AIG - Payment Three-Way Match created (v4)")

log("")
log("C) withholding wiring audit (Section 4.2)")
from frappe.model import meta as _meta

flds = [f.fieldname for f in _meta.get_meta("Tax Withholding Rate").fields]
log("  TWR fields:", flds)
for cat in ["AIG 7.5% VAT Withholding", "AIG 3% Withholding Tax"]:
    rates = frappe.get_all("Tax Withholding Rate", filters={"parent": cat},
                           fields=["*"])
    for r in rates:
        acct = r.get("account") or r.get("account_head")
        log(f"  {cat}: rate={r.get('tax_withholding_rate')} "
            f"account={acct} thresholds=({r.get('single_threshold')}, "
            f"{r.get('cumulative_threshold')})")
exp = {"AIG 7.5% VAT Withholding": "2132", "AIG 3% Withholding Tax": "2133"}
bad = []
for cat, prefix in exp.items():
    rates = frappe.get_all("Tax Withholding Rate", filters={"parent": cat},
                           fields=["*"])
    for r in rates:
        acct = r.get("account") or r.get("account_head") or ""
        if not str(acct).startswith(prefix):
            bad.append(f"{cat} -> {acct} (expected {prefix}*)")
log(f"  account wiring: {'OK' if not bad else 'MISMATCH: ' + str(bad)}")

pe_fields = [f.fieldname for f in frappe.get_meta("Payment Entry").fields]
if "tax_withholding_category" in pe_fields:
    std = frappe.get_meta("Payment Entry").get_field("tax_withholding_category")
    log(f"  Payment Entry has STANDARD tax_withholding_category "
        f"(fieldtype={std.fieldtype}, hidden={std.hidden})")
else:
    log("  Payment Entry has NO tax_withholding_category field - a custom "
        "field + script would be needed to apply TWC at payment time")

frappe.clear_cache()
log("")
log("DONE 133")
