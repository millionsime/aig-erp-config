# 130_procurement_refine_inspect.py -- READ-ONLY inspection required by the
# refined procurement/payment brief (Section 1) before any change. Covers:
# company/FY/CC/CoA state, AIG roles + assignments, existing workflows on
# Material Request / Purchase Order / Payment Entry (states + transitions),
# User Permissions / Budgets / TWCs, existing procurement/payment server
# scripts, custom fields (estimated total, Model 42, committee), open docs,
# and a "CEO" wording audit on the Enterprise Head path.

import json

import frappe


def log(*a):
    print(*a, flush=True)


def sec(t):
    log("")
    log("=" * 8, t, "=" * 8)


sec("A. Company / Fiscal Year / Cost Center / CoA")
log("companies:", frappe.get_all("Company", pluck="name"))
log("fiscal years:", frappe.get_all("Fiscal Year", pluck="name"))
log("cost centers:", frappe.db.count("Cost Center", {"company": "Adama Investment Group"}))
log("accounts:", frappe.db.count("Account", {"company": "Adama Investment Group"}))

sec("B. AIG roles + user assignments")
ROLES = ["AIG Procurement Officer", "AIG Purchase Committee", "AIG Enterprise Head",
         "AIG Corporate", "AIG CEO", "AIG Finance", "AIG Deputy",
         "AIG Evaluation Committee", "AIG Main Store Administrator",
         "AIG Store Keeper", "AIG End User", "AIG Inventory Administrator"]
for r in ROLES:
    exists = frappe.db.exists("Role", r)
    users = frappe.get_all("Has Role", filters={"role": r, "parenttype": "User"},
                           pluck="parent") if exists else []
    log(f"  {r}: exists={bool(exists)} users={users}")

sec("C. Workflows on MR / PO / PE")
for dt in ["Material Request", "Purchase Order", "Payment Entry"]:
    wfs = frappe.get_all("Workflow", filters={"document_type": dt},
                         fields=["name", "is_active", "workflow_state_field",
                                 "override_status"])
    for w in wfs:
        log(f"  {dt}: {w.name} active={w.is_active} field={w.workflow_state_field}")
        for s in frappe.get_all("Workflow Document State",
                                filters={"parent": w.name},
                                fields=["state", "doc_status", "allow_edit", "idx"],
                                order_by="idx"):
            log(f"    state: {s.state!r} doc_status={s.doc_status} allow_edit={s.allow_edit}")
        for t in frappe.get_all("Workflow Transition",
                                filters={"parent": w.name},
                                fields=["state", "action", "next_state", "allowed",
                                        "condition", "idx"],
                                order_by="idx"):
            log(f"    trans : {t.state!r} --[{t.action}]({t.allowed}; "
                f"cond={t.condition!r})--> {t.next_state!r}")
    if not wfs:
        log(f"  {dt}: (no workflow)")

sec("D. User Permissions (procurement-relevant users)")
for u in ["procurement.agro@aig.local", "procurement.construction@aig.local",
          "head.agro@aig.local", "head.construction@aig.local",
          "head.service@aig.local", "committee1@aig.local",
          "corporate@aig.local", "ceo@aig.local", "deputy@aig.local",
          "finance@aig.local"]:
    if not frappe.db.exists("User", u):
        log(f"  {u}: (user missing)")
        continue
    rows = frappe.get_all("User Permission", filters={"user": u},
                          fields=["allow", "for_value", "applicable_for"])
    log(f"  {u}: {[(r.allow, r.for_value, r.applicable_for) for r in rows]}")

sec("E. Budgets")
log("budgets:", frappe.get_all("Budget",
                              filters={"company": "Adama Investment Group"},
                              pluck="name"))

sec("F. Purchase Taxes and Charges Templates + Tax Withholding Categories")
for r in frappe.get_all("Purchase Taxes and Charges Template",
                        filters={"company": "Adama Investment Group"},
                        fields=["name", "disabled", "is_default"]):
    cats = frappe.get_all("Purchase Taxes and Charges",
                          filters={"parent": r.name},
                          fields=["category", "account_head", "rate",
                                  "add_deduct_tax"])
    log(f"  {r.name} disabled={r.disabled} default={r.is_default}")
    for c in cats:
        log(f"    {c}")

log("TWCs:")
from frappe.model import meta as _meta
for r in frappe.get_all("Tax Withholding Category", fields=["name"],
                        order_by="name"):
    flds = [f.fieldname for f in _meta.get_meta("Tax Withholding Rate").fields]
    keep = [f for f in flds if f in ("from_date", "to_date", "tax_withholding_rate",
                                     "account", "account_head", "rate",
                                     "single_threshold", "cumulative_threshold",
                                     "threshold_type")]
    rates = frappe.get_all("Tax Withholding Rate",
                           filters={"parent": r.name},
                           fields=["*"])
    slim = [{k: row.get(k) for k in keep} for row in rates]
    log(f"  {r.name}: {slim}")

sec("G. Server Scripts (procurement/payment related)")
for r in frappe.get_all("Server Script",
                        filters={"reference_doctype": ["in", ["Material Request",
                                                              "Purchase Order",
                                                              "Payment Entry",
                                                              "Purchase Receipt",
                                                              "Purchase Invoice"]]},
                        fields=["name", "reference_doctype", "script_type",
                                "disabled"],
                        order_by="reference_doctype, name"):
    log(f"  {r}")

sec("H. Custom fields in scope")
for r in frappe.get_all("Custom Field",
                        filters={"dt": ["in", ["Material Request", "Purchase Order",
                                               "Payment Entry", "Purchase Receipt",
                                               "Purchase Invoice"]]},
                        fields=["dt", "fieldname", "fieldtype", "label",
                                "reqd", "read_only"],
                        order_by="dt, fieldname"):
    log(f"  {r}")

sec("I. Custom doctypes (committee signoff?)")
log("aig-related doctypes:",
    frappe.get_all("DocType", filters={"name": ["like", "AIG%"]}, pluck="name"))

sec("J. Open documents in scope")
for dt in ["Material Request", "Purchase Order", "Payment Entry",
           "Purchase Receipt", "Purchase Invoice"]:
    rows = frappe.get_all(dt, filters={"docstatus": 0},
                          fields=["name", "workflow_state"], limit=15,
                          order_by="name")
    log(f"  {dt} drafts: {[(r.name, r.get('workflow_state')) for r in rows]}")

sec("K. 'CEO' wording audit (labels/buttons/print formats/descriptions)")
hits = []
for r in frappe.get_all("Custom Field",
                        filters={"dt": ["in", ["Material Request", "Purchase Order",
                                               "Payment Entry", "Purchase Receipt"]]},
                        fields=["dt", "fieldname", "label", "description"]):
    for f in ("label", "description"):
        v = getattr(r, f) or ""
        if "CEO" in v:
            hits.append(f"CustomField {r.dt}.{r.fieldname}.{f}={v!r}")
for r in frappe.get_all("Print Format",
                        filters={"doc_type": ["in", ["Purchase Order", "Payment Entry",
                                                     "Material Request"]]},
                        fields=["name", "doc_type"]):
    body = frappe.db.get_value("Print Format", r.name, "print_format_body") or ""
    if "CEO" in body:
        hits.append(f"PrintFormat {r.name}: 'CEO' found")
log("hits:", hits if hits else "(none -- clean)")

sec("L. Payment TWC account wiring on Payment Entry custom fields")
for r in frappe.get_all("Custom Field",
                        filters={"dt": "Payment Entry",
                                 "fieldname": ["like", "%withhold%"]},
                        fields=["fieldname", "fieldtype", "label", "reqd"]):
    log(f"  {r}")
if not frappe.get_all("Custom Field",
                      filters={"dt": "Payment Entry",
                               "fieldname": ["like", "%withhold%"]}):
    log("  (no withholding custom fields on Payment Entry)")
