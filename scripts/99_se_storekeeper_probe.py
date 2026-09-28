# 99_se_storekeeper_probe.py -- Reproduce the "Not permitted: read on Stock
# Entry new-stock-entry-..." toast. The desk calls a READ permission check on
# the unsaved doc when a workflow is active; if any auto-filled field is
# outside the user's User Permission scope, the check fails. Test the doc-level
# read check for storekeeper.agro with: no cost center, Company-default CC
# (Head Office - AIG), and own-enterprise CC (Dairy Farm - AIG). Also dump the
# SE server scripts to see what they stamp on save.

import frappe
from frappe.model.workflow import get_transitions

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"


def log(*a):
    print(*a, flush=True)


def probe(label, cost_center=None, aig_cc=None, warehouse="Dairy Farm Store - AIG"):
    frappe.set_user(U)
    doc = frappe.new_doc("Stock Entry")
    doc.company = COMPANY
    doc.stock_entry_type = "Material Receipt"
    doc.purpose = "Material Receipt"
    doc.to_warehouse = warehouse
    doc.append("items", {
        "item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
        "t_warehouse": warehouse,
        **({"cost_center": cost_center} if cost_center else {}),
    })
    if aig_cc:
        doc.aig_cost_center = aig_cc
    doc.name = "new-stock-entry-evkvhxjiqj"  # mimic the client temp name
    try:
        frappe.has_permission(doc, "read", user=U, throw=True)
        res = "READ OK"
    except Exception:
        res = "READ FAIL: " + frappe.get_traceback().strip().splitlines()[-1][:100]
    try:
        get_transitions(doc, user=U)
        tr = "transitions OK"
    except Exception:
        tr = "transitions FAIL: " + frappe.get_traceback().strip().splitlines()[-1][:100]
    frappe.set_user("Administrator")
    log(f"  {label}:")
    log(f"    {res}")
    log(f"    {tr}")


log("PROBE A: no cost center set")
probe("empty CC")
log("")
log("PROBE B: Company default CC = Head Office - AIG (what the form auto-fills)")
probe("HO CC", cost_center="Head Office - AIG", aig_cc="Head Office - AIG")
log("")
log("PROBE C: own-enterprise CC = Dairy Farm - AIG")
probe("Dairy CC", cost_center="Dairy Farm - AIG", aig_cc="Dairy Farm - AIG")

log("")
log("SERVER SCRIPTS (what gets stamped on save)")
for name in ["AIG - SE Movement Defaults", "AIG - SE Item Cost Center Sync"]:
    s = frappe.db.get_value("Server Script", name, "script")
    log(f"--- {name} ---")
    log((s or "(missing)")[:900])
