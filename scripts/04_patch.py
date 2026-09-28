# AIG config - step 04 patch:
# 1) Rewrite the Payment Three-Way Match server script (PE references cannot
#    include Purchase Receipts, so Model 19 is verified by querying submitted
#    Purchase Receipt Items linked to the referenced POs).
# 2) Grant submit to Procurement Officer (PO) and Finance (PE): the workflow
#    Draft->pending transition performs the doc submission.
import frappe

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


THREE_WAY_V2 = """# AIG Three-Way Match (Payment Entry, Before Submit) - v3
# Payment is made against the supplier's Purchase Invoice (the only reference a
# Payment Entry needs; adding the PO too would double-count the allocation).
# The three legs are proven FROM that invoice:
#   1) payment_type must be Pay
#   2) at least one Purchase Invoice reference with non-zero allocation
#   3) paid_amount reconciles with the invoice allocation (tolerance 0.5%, min 10 ETB)
#   4) each invoice line is linked to a Purchase Order  (leg: PO)
#   5) each such Purchase Order has at least one SUBMITTED Purchase Receipt
#      (leg: Model 19, via Purchase Receipt Item.purchase_order)
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
    frappe.throw("AIG Three-Way Match failed: no Purchase Invoice reference (supplier invoice).")

paid = doc.paid_amount or 0

def tol(x):
    return max(10, 0.005 * abs(x))

if abs(pi_total - paid) > tol(pi_total):
    frappe.throw("AIG Three-Way Match failed: paid {0} vs invoice allocation {1} mismatch.".format(paid, pi_total))

for pi in pi_names:
    pos = []
    for row in frappe.db.get_all("Purchase Invoice Item", filters={"parent": pi}, fields=["purchase_order"]):
        if row.purchase_order and row.purchase_order not in pos:
            pos.append(row.purchase_order)
    if not pos:
        frappe.throw("AIG Three-Way Match failed: Purchase Invoice {0} is not linked to a Purchase Order.".format(pi))
    for po in pos:
        receipts = frappe.db.get_all("Purchase Receipt Item",
                                     filters={"purchase_order": po, "docstatus": 1},
                                     fields=["parent"])
        if not receipts:
            frappe.throw("AIG Three-Way Match failed: no submitted Purchase Receipt (Model 19) for Purchase Order {0}.".format(po))
"""

ss = frappe.get_doc("Server Script", "AIG - Payment Three-Way Match")
ss.script = THREE_WAY_V2
ss.flags.ignore_permissions = True
ss.save(ignore_permissions=True)
log("UPDATE", "Server Script AIG - Payment Three-Way Match -> v3 (PI-centric: PO + Model 19 derived from invoice)")


def ensure_perm(dt, role, **flags):
    row_name = frappe.db.get_value("Custom DocPerm", {"parent": dt, "role": role, "permlevel": 0})
    if not row_name:
        print(f"!! no base perm row for {dt}/{role}")
        return
    doc = frappe.get_doc("Custom DocPerm", row_name)
    changed = False
    for k, v in flags.items():
        if getattr(doc, k) != v:
            setattr(doc, k, v)
            changed = True
    if changed:
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
        log("UPDATE", f"DocPerm {dt}/{role}: {flags}")


ensure_perm("Purchase Order", "AIG Procurement Officer", submit=1)
ensure_perm("Payment Entry", "AIG Finance", submit=1)

frappe.db.commit()
print(f"STEP04_COMPLETE {len(LOG)} actions")

def run():
    frappe.db.commit()
    return len(LOG)

