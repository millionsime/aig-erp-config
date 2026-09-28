# Budget consumption per Cost Center: post -> verify -> cancel -> verify.
from frappe.desk.query_report import get_report_result

FILTERS = {
    "company": "Adama Investment Group",
    "from_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "to_fiscal_year": "FY 2019 EC (Jul 2026 - Jul 2027)",
    "period": "Yearly",
    "periodicity": "Yearly",
    "budget_against": "Cost Center",
}

def dairy_actual():
    res = get_report_result(frappe.get_doc("Report", "Budget Variance Report"), FILTERS)
    for r in res[1]:
        if r.get("budget_against") == "Dairy Farm - AIG":
            for k, v in r.items():
                if k.startswith("actual"):
                    return v or 0
    return 0

before = dairy_actual()
print("Dairy actual BEFORE test JE:", before)

je = frappe.get_doc({
    "doctype": "Journal Entry",
    "entry_type": "Journal Entry",
    "company": "Adama Investment Group",
    "posting_date": "2026-09-25",
    "remark": "AIG FOUNDATION TEST: budget consumption check (to be cancelled)",
    "accounts": [
        {"account": "Cost of Goods Sold - AIG", "debit_in_account_currency": 5000,
         "credit_in_account_currency": 0, "cost_center": "Dairy Farm - AIG",
         "user_remark": "AIG foundation budget consumption test"},
        {"account": "Cash - AIG", "debit_in_account_currency": 0,
         "credit_in_account_currency": 5000, "cost_center": "Dairy Farm - AIG",
         "user_remark": "AIG foundation budget consumption test"},
    ],
})
je.insert()
je.submit()
frappe.db.commit()
print("POSTED test JE:", je.name)

during = dairy_actual()
print("Dairy actual DURING (expect +5000):", during)
assert abs(during - (before + 5000)) < 1, "Budget Variance did not pick up the test consumption!"

je.cancel()
frappe.db.commit()
print("CANCELLED test JE:", je.name)

after = dairy_actual()
print("Dairy actual AFTER cancel (expect baseline):", after)
assert abs(after - before) < 1, "Cancelled entries still counted in Budget Variance!"

print("\n*** PASS: Budget Variance Report shows consumption per Cost Center,")
print("*** and cancelled test entries are correctly excluded.")
print("\nDONE-G2")
