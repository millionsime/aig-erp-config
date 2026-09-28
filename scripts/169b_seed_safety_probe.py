# 169b_seed_safety_probe.py -- READ-ONLY final pre-seed probe: JE/PE guard
# texts, VAT accounts + tax templates, workflow transition maps, JE meta.
import frappe
import json

COMPANY = "Adama Investment Group"

def log(*a):
    print(*a, flush=True)

log("=== 1. Guard script texts (JE + PE three-way + PE raw) ===")
for name in ["AIG - CC Guard Journal Entry", "AIG - Payment Three-Way Match",
             "AIG - PE Guard Raw Submit", "AIG - CC Guard Sales Invoice",
             "AIG - CC Guard Purchase Invoice"]:
    txt = frappe.db.get_value("Server Script", name, "script")
    log(f"--- {name} ---")
    log(txt if txt else "(NOT FOUND)")

log("")
log("=== 2. VAT / tax accounts ===")
for a in frappe.get_all("Account", filters={"company": COMPANY, "name": ["like", "%VAT%"]},
                        fields=["name", "account_number", "root_type", "account_type", "is_group"],
                        order_by="account_number"):
    log(f"  {a.name} | {a.root_type} | {a.account_type} | group={a.is_group}")

log("")
log("=== 3. Tax templates ===")
for t in frappe.get_all("Purchase Taxes and Charges Template", fields=["name", "company"], limit=10):
    log("  PUR:", t.name)
for t in frappe.get_all("Sales Taxes and Charges Template", fields=["name", "company"], limit=10):
    log("  SAL:", t.name)
row = frappe.db.get_value("Purchase Taxes and Charges Template", "Ethiopia Tax - AIG", "name")
if row:
    d = frappe.get_doc("Purchase Taxes and Charges Template", "Ethiopia Tax - AIG")
    for t in d.taxes:
        log("  Ethiopia Tax - AIG row:", t.charge_type, t.rate, "->", t.account_head)

log("")
log("=== 4. JE meta: cost-center-ish fields ===")
m = frappe.get_meta("Journal Entry")
log("  ", [f.fieldname for f in m.fields if "cost" in f.fieldname or "aig" in f.fieldname or f.fieldtype == "Table"])
am = frappe.get_meta("Journal Entry Account")
log("  JE Account child:", [f.fieldname for f in am.fields if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Button")][:40])

log("")
log("=== 5. Workflow transition maps (state, action, next_state, role) ===")
from frappe.model.workflow import get_transitions
frappe.set_user("Administrator")
for wname in ["AIG Procurement Approval", "AIG Payment Approval", "AIG Stock Request Approval"]:
    w = frappe.get_doc("Workflow", wname)
    log(f"--- {wname} ({w.document_type}) ---")
    for t in w.transitions:
        log(f"  {t.state} --[{t.action}]--> {t.state_next_state if hasattr(t,'state_next_state') else t.get('state')} | role={t.allowed}")
    # transitions uses field 'state' and 'next_state' on Workflow Transition Master? inspect
    if w.transitions:
        log("  raw row keys:", list(w.transitions[0].as_dict().keys()))

log("")
log("=== 6. Customer mandatory-ish + naming ===")
cm = frappe.get_meta("Customer")
log("  naming_series options:", frappe.get_meta("Customer").get_field("naming_series").options if cm.get_field("naming_series") else None)
log("  customer_group default:", frappe.db.get_value("Customer Group", {"is_group": 0}, "name"))
log("  territory default:", frappe.db.get_value("Territory", {"is_group": 0}, "name"))

log("")
log("=== 7. SR child meta (BOM-less) ===")
im = frappe.get_meta("Stock Reconciliation Item")
log("  ", [f.fieldname for f in im.fields if f.fieldtype not in ("Section Break", "Column Break", "HTML", "Button")][:30])

log("")
log("=== 8. Payment Entry meta deduction field ===")
pm = frappe.get_meta("Payment Entry Deduction")
log("  PE Deduction child:", [f.fieldname for f in pm.fields if f.fieldtype not in ("Section Break", "Column Break")])

log("DONE")
