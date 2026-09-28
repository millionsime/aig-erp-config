# 135_changelog_facts.py -- READ-ONLY: facts for the procurement refine changelog.
import frappe


def log(*a):
    print(*a, flush=True)


log("AIG server scripts (procurement/payment scope):")
for r in frappe.get_all("Server Script",
                        fields=["name", "reference_doctype", "doctype_event",
                                "disabled"],
                        order_by="name"):
    log(f"  {r.name} | {r.reference_doctype} | {r.doctype_event} | "
        f"disabled={r.disabled}")

log("")
log("custom fields:")
for dt in ["Material Request", "Purchase Order", "Purchase Receipt",
           "Payment Entry", "Purchase Invoice"]:
    rows = frappe.get_all("Custom Field", filters={"dt": dt},
                          fields=["fieldname", "label", "fieldtype", "reqd"],
                          order_by="idx")
    log(f"  {dt}:")
    for r in rows:
        log(f"    {r.fieldname} ({r.fieldtype}, reqd={r.reqd}) - {r.label}")

log("")
log("AIG doctypes:")
for r in frappe.get_all("DocType", filters={"module": "AIG HR"},
                        fields=["name"], order_by="name"):
    log(f"  {r.name}")

log("")
log("budgets:")
log(f"  Budget records: {len(frappe.get_all('Budget'))}")

log("")
log("withholding categories:")
for cat in ["AIG 7.5% VAT Withholding", "AIG 3% Withholding Tax"]:
    rows = frappe.get_all("Tax Withholding Account",
                          filters={"parent": cat},
                          fields=["company", "account"])
    rates = frappe.get_all("Tax Withholding Rate", filters={"parent": cat},
                           fields=["tax_withholding_rate", "tax_withholding_group"])
    log(f"  {cat}: accounts={[(r.company, r.account) for r in rows]} "
        f"rates={[(r.tax_withholding_rate, r.tax_withholding_group) for r in rates]}")

log("")
log("supplier TWC defaults (must be empty to avoid double-withholding):")
for s in frappe.get_all("Supplier", fields=["name", "tax_withholding_category",
                                            "tax_withholding_group"]):
    if s.tax_withholding_category or s.tax_withholding_group:
        log(f"  {s.name}: cat={s.tax_withholding_category} grp={s.tax_withholding_group}")
log("  (suppliers not listed above carry no TWC default)")

log("")
log("tax template:")
tt = frappe.get_doc("Sales Taxes and Charges Template", "Ethiopia Tax - AIG")
for t in tt.taxes:
    log(f"  {t.account_head} rate={t.rate} type={t.charge_type} "
        f"included={t.included_in_print_rate}")

log("")
log("READ-ONLY DUMP DONE")
