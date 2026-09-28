# Remove batch-harness artifacts: any PO left submitted (docstatus=1) but stuck in
# a "Pending ..." workflow state. In live per-request use the budget Stop rolls the
# submit back and the PO stays Draft; the batch acceptance commits once at the end,
# so the pre-on_submit write can linger. These are not valid demo docs.
import frappe

bad = frappe.get_all("Purchase Order",
                     filters={"docstatus": 1, "workflow_state": ["like", "Pending%"]},
                     pluck="name")
print("inconsistent submitted-but-pending POs:", bad)
for name in bad:
    d = frappe.get_doc("Purchase Order", name)
    d.flags.ignore_permissions = True
    try:
        d.cancel()
    except Exception as e:
        print("cancel note:", name, e)
    frappe.delete_doc("Purchase Order", name, ignore_permissions=True, force=True)
    print("DELETED", name)
frappe.db.commit()

print("\n=== FINAL DEMO POs ===")
for d in frappe.get_all("Purchase Order", fields=["name", "docstatus", "workflow_state", "grand_total", "aig_cost_center"], order_by="name"):
    print(" ", d)
print("CLEAN_DONE")
