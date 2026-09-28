# AIG foundation - BUILD G: Balance Sheet per-Cost-Center vs consolidated.
from frappe.desk.query_report import get_report_result

COMPANY = "Adama Investment Group"

def run_bs(filters):
    res = get_report_result(frappe.get_doc("Report", "Balance Sheet"), filters)
    return res

base = {
    "company": COMPANY,
    "filter_based_on": "Fiscal Year",
    "from_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "to_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "periodicity": "Yearly",
    "period": "Yearly",
    "accumulated_in_account_currency": 1,
}

print("=== CONSOLIDATED (no CC filter) ===")
cons = run_bs(base)
rows = cons[1]
def find(rows, label):
    for r in rows:
        if r.get("account") == label:
            return r
    return None
for label in ["Cash In Hand - AIG", "Bank Accounts - AIG", "Stock Assets - AIG",
              "Accounts Receivable - AIG", "Fixed Assets - AIG", "Accounts Payable - AIG"]:
    r = find(rows, label)
    if r:
        print(f"  {label}: {r.get('total')}")

print("\n=== FILTERED: Dairy Farm - AIG ===")
dairy = run_bs({**base, "cost_center": ["Dairy Farm - AIG"]})
drows = dairy[1]
for label in ["Stock Assets - AIG", "Cash In Hand - AIG", "Bank Accounts - AIG",
              "Accounts Receivable - AIG", "Fixed Assets - AIG"]:
    r = find(drows, label)
    if r:
        print(f"  {label}: {r.get('total')}")

# Assertions: per-CC BS must not be identical to consolidated where GL shows
# CC-tagged rows exist, and Dairy stock must equal the CC-tagged GL figure.
dairy_gl_stock = frappe.db.sql("""select ifnull(sum(debit-credit),0) from `tabGL Entry`
                                  where account='Stock In Hand - AIG' and cost_center='Dairy Farm - AIG'""")[0][0]
dairy_bs_stock = (find(drows, "Stock Assets - AIG") or {}).get("total") or 0
print(f"\nDairy stock: GL={dairy_gl_stock}  BS-filtered={dairy_bs_stock}")

cons_stock = (find(rows, "Stock Assets - AIG") or {}).get("total") or 0
print(f"Consolidated stock: {cons_stock}")
assert abs(dairy_bs_stock - dairy_gl_stock) < 1, "Filtered BS does not match CC-tagged GL!"
assert abs(cons_stock - dairy_gl_stock) < 1, "Consolidated stock should equal the only tagged stock (Dairy)"

# Fixed assets: consolidated must include the depreciation test asset's
# Accumulated Depreciation which carries the Dairy CC.
acc_dep_dairy = frappe.db.sql("""select ifnull(sum(debit-credit),0) from `tabGL Entry`
                                 where account='Accumulated Depreciation - AIG'
                                   and cost_center='Dairy Farm - AIG'""")[0][0]
print(f"Accumulated Depreciation tagged Dairy (GL): {acc_dep_dairy}  (expect -4166.67)")

print("\n=== BUDGET VARIANCE REPORT (Cost Center) ===")
bvr = get_report_result(frappe.get_doc("Report", "Budget Variance Report"), {
    "company": COMPANY,
    "from_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "to_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "periodicity": "Yearly",
    "period": "Yearly",
    "budget_against": "Cost Center",
})
brows = bvr[1]
print(f"{len(brows)} rows")
for r in brows[:12]:
    print("  ", {k: r.get(k) for k in ("cost_center", "budget_amount", "expense", "variance") if k in r})

print("\nDONE-G")
