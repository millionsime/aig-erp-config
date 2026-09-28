# 21 - Deploy the correct v3 (PI-centric, RestrictedPython-safe) Three-Way Match
# script, then validate: (a) it compiles, (b) committee has an action on the
# pending PO, (c) the demo Payment Entry satisfies the three-way match WITHOUT
# actually submitting it (so the demo doc stays Draft for the live run).
import frappe
from frappe.model.workflow import get_transitions

V3 = """# AIG Three-Way Match (Payment Entry, Before Submit) - v3
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

# (a) deploy + compile-check -------------------------------------------------
ss = frappe.get_doc("Server Script", "AIG - Payment Three-Way Match")
ss.script = V3
ss.flags.ignore_permissions = True
ss.save(ignore_permissions=True)
frappe.db.commit()
saved = frappe.db.get_value("Server Script", "AIG - Payment Three-Way Match", "script")
print("Deployed v3. Still contains '_tol'? ", "_tol" in (saved or ""))

from RestrictedPython import compile_restricted
try:
    compile_restricted(V3, filename="<threeway>", mode="exec")
    print("RestrictedPython compile: OK")
except SyntaxError as e:
    print("RestrictedPython compile FAILED:", e)

# (b) committee action on the pending Proforma PO ---------------------------
frappe.set_user("committee1@aig.local")
try:
    doc = frappe.get_doc("Purchase Order", "PUR-ORD-2026-00005")
    acts = sorted({t.action for t in get_transitions(doc)})
    print("committee1 actions on PUR-ORD-2026-00005:", acts)
except Exception as e:
    print("committee1 on 00005 BLOCKED:", type(e).__name__, e)
frappe.set_user("Administrator")

# (c) dry three-way match on the demo PE (no submit) ------------------------
pe = frappe.get_doc("Payment Entry", "ACC-PAY-2026-00003")
pi_names, pi_total = [], 0.0
for r in pe.references:
    if r.reference_doctype == "Purchase Invoice" and (r.allocated_amount or 0) > 0:
        pi_names.append(r.reference_name)
        pi_total += r.allocated_amount
paid = pe.paid_amount or 0
tolerance = max(10, 0.005 * abs(pi_total))
print(f"PE refs: PI={pi_names} pi_total={pi_total} paid={paid} within_tol={abs(pi_total-paid) <= tolerance}")
for pi in pi_names:
    pos = [x.purchase_order for x in frappe.db.get_all("Purchase Invoice Item",
           filters={"parent": pi}, fields=["purchase_order"]) if x.purchase_order]
    print(f"  PI {pi} -> POs {pos}")
    for po in pos:
        rc = frappe.db.get_all("Purchase Receipt Item",
               filters={"purchase_order": po, "docstatus": 1}, fields=["parent"])
        print(f"    PO {po} submitted receipts: {[x.parent for x in rc]}")

print("PE state (should still be Draft):", frappe.db.get_value("Payment Entry", pe.name, "workflow_state"))
print("FIX_DONE")
