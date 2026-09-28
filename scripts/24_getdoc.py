import frappe
import traceback
from frappe.desk.form.load import getdoc

CASES = [
    ("committee1@aig.local", "Purchase Order", "PUR-ORD-2026-00005"),
    ("head.agro@aig.local", "Purchase Order", "PUR-ORD-2026-00005"),
    ("ceo@aig.local", "Purchase Order", "PUR-ORD-2026-00006"),
    ("finance@aig.local", "Payment Entry", "ACC-PAY-2026-00003"),
    ("deputy@aig.local", "Payment Entry", "ACC-PAY-2026-00003"),
]

for user, dt, dn in CASES:
    frappe.set_user(user)
    try:
        getdoc(dt, dn)
        # also emulate the workflow-transition computation the form uses
        from frappe.model.workflow import get_transitions
        doc = frappe.get_doc(dt, dn)
        acts = sorted({t.action for t in get_transitions(doc)})
        print(f"[OK]    {user:32s} {dt}/{dn} actions={acts}")
    except Exception as e:
        print(f"[THROW] {user:32s} {dt}/{dn} -> {type(e).__name__}: {str(e)[:180]}")
    frappe.set_user("Administrator")

print("\nGETDOC_DONE")
