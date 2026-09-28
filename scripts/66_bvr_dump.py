# Dump Budget Variance Report raw result (read-only).
from frappe.desk.query_report import get_report_result

res = get_report_result(frappe.get_doc("Report", "Budget Variance Report"), {
    "company": "Adama Investment Group",
    "from_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "to_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "period": "Yearly",
    "periodicity": "Yearly",
    "budget_against": "Cost Center",
})
cols = [c.get("fieldname") for c in res[0]]
print("columns:", cols)
print()
for r in res[1]:
    print({k: r.get(k) for k in cols if r.get(k) not in (None, 0, "", [])})
print("DONE")
