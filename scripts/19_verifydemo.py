# 19 - Verify the freshly-added demo docs are ready to be driven through the UI.
import frappe
from frappe.model.workflow import get_transitions

def actions_for(user, dt, dn):
    frappe.set_user(user)
    try:
        doc = frappe.get_doc(dt, dn)
        ts = get_transitions(doc)
        acts = sorted({t.action for t in ts})
        readable = "readable"
    except Exception as e:
        acts = []
        readable = f"BLOCKED ({type(e).__name__})"
    frappe.set_user("Administrator")
    return acts, readable

rows = [
    ("PUR-ORD-2026-00004", "Purchase Order", "procurement.agro@aig.local",         "Direct 15k"),
    ("PUR-ORD-2026-00005", "Purchase Order", "procurement.agro@aig.local",         "Proforma 250k"),
    ("PUR-ORD-2026-00006", "Purchase Order", "procurement.construction@aig.local", "Bulky 900k"),
    ("ACC-PAY-2026-00003", "Payment Entry",  "finance@aig.local",                  "Payment 400k"),
]
for dn, dt, user, label in rows:
    st = frappe.db.get_value(dt, dn, "workflow_state")
    ds = frappe.db.get_value(dt, dn, "docstatus")
    acts, readable = actions_for(user, dt, dn)
    print(f"{label:16s} {dn:22s} state={st:12s} docstatus={ds} | {user:34s} {readable} actions={acts}")

# cross-enterprise scoping sanity: agro officer must NOT see the Construction PO
frappe.set_user("procurement.agro@aig.local")
sees = frappe.get_list("Purchase Order", pluck="name")
frappe.set_user("Administrator")
print("\nprocurement.agro sees POs:", sorted(sees))
print("Construction PO visible to agro officer? ", "PUR-ORD-2026-00006" in sees)

print("\nVERIFY_DEMO_DONE")
