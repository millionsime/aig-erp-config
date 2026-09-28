# AIG foundation - ACCEPTANCE CHECKLIST (brief Section 9), executable.
from frappe.desk.query_report import get_report_result

COMPANY = "Adama Investment Group"
FY19 = "FY 2019 EC (Jul 2026 - Jul 2027)"
results = []

def check(label, fn):
    try:
        fn()
        results.append(("PASS", label))
        print("PASS ", label)
    except Exception as e:
        results.append(("FAIL", label))
        print("FAIL ", label, "->", e)

# 1. Company: single, ETB, Ethiopia
def _company():
    comps = frappe.get_all("Company", pluck="name")
    assert comps == [COMPANY], f"companies: {comps}"
    cur, country = frappe.db.get_value("Company", COMPANY, ["default_currency", "country"])
    assert cur == "ETB" and country == "Ethiopia"
check("Company exists (single) with ETB + Ethiopia", _company)

# 2. Fiscal Years: EC-labelled, correct Gregorian ranges, company-linked
def _fy():
    fy18 = frappe.db.get_value("Fiscal Year", "FY 2018 EC (Jul 2025 - Jul 2026)",
                               ["year_start_date", "year_end_date"], as_dict=True)
    fy19 = frappe.db.get_value("Fiscal Year", FY19, ["year_start_date", "year_end_date"], as_dict=True)
    assert fy18 and str(fy18.year_start_date) == "2025-07-08" and str(fy18.year_end_date) == "2026-07-07"
    assert fy19 and str(fy19.year_start_date) == "2026-07-08" and str(fy19.year_end_date) == "2027-07-07"
    linked = {r.parent for r in frappe.get_all("Fiscal Year Company",
              filters={"company": COMPANY}, fields=["parent"])}
    assert {"FY 2018 EC (Jul 2025 - Jul 2026)", FY19} <= linked
check("Fiscal Years EC-labelled with correct ranges, both linked to company", _fy)

# 3. CoA consolidated design: natural accounts exist ONCE; control accounts; one RE
def _coa():
    n_salary = frappe.db.count("Account", {"account_name": "Salary", "company": COMPANY})
    assert n_salary == 1, f"Salary accounts: {n_salary}"
    n_dep = frappe.db.count("Account", {"account_name": "Depreciation", "company": COMPANY})
    n_accdep = frappe.db.count("Account", {"account_name": "Accumulated Depreciation", "company": COMPANY})
    assert n_dep == 1 and n_accdep == 1
    n_bankchg = frappe.db.count("Account", {"account_name": "Bank Charges", "company": COMPANY})
    assert n_bankchg == 1
    n_re = frappe.db.count("Account", {"account_name": "Retained Earnings", "company": COMPANY})
    assert n_re == 1, f"Retained Earnings accounts: {n_re}"
    debtors = frappe.get_all("Account", filters={"account_name": "Debtors", "company": COMPANY}, pluck="name")
    creditors = frappe.get_all("Account", filters={"account_name": "Creditors", "company": COMPANY}, pluck="name")
    assert len(debtors) == 1 and len(creditors) == 1
    bank = frappe.db.get_value("Account", "Commercial Bank of Ethiopia - AIG", "root_type")
    assert bank == "Asset", f"CBE root_type={bank} (must be Asset)"
check("CoA consolidated: natural accounts once, control accounts, single Retained Earnings, CBE is Asset", _coa)

# 4. No customer/vendor names as GL accounts
def _party_accounts():
    parties = set(frappe.get_all("Customer", pluck="name")) | set(frappe.get_all("Supplier", pluck="name"))
    acc_rows = frappe.get_all("Account", filters={"company": COMPANY}, pluck="account_name")
    acc_names = set(acc_rows)
    overlap = {p for p in parties if p in acc_names}
    assert not overlap, f"party-named accounts: {overlap}"
check("No individual customer/vendor names exist as GL accounts", _party_accounts)

# 5. Cost Center tree per brief
def _cc():
    expect = {
        "Adama Investment Group - AIG": (None, 1),
        "Head Office - AIG": ("Adama Investment Group - AIG", 0),
        "Agro Enterprise - AIG": ("Adama Investment Group - AIG", 1),
        "Dairy Farm - AIG": ("Agro Enterprise - AIG", 0),
        "Poultry Farm - AIG": ("Agro Enterprise - AIG", 0),
        "Slaughterhouse - AIG": ("Agro Enterprise - AIG", 0),
        "Animal Feed Factory - AIG": ("Agro Enterprise - AIG", 0),
        "Construction Enterprise - AIG": ("Adama Investment Group - AIG", 1),
        "Construction Projects - AIG": ("Construction Enterprise - AIG", 1),
        "Integrated Service Enterprise - AIG": ("Adama Investment Group - AIG", 1),
        "Fuel Station - AIG": ("Integrated Service Enterprise - AIG", 0),
        "City Mall - AIG": ("Integrated Service Enterprise - AIG", 0),
        "Garage - AIG": ("Integrated Service Enterprise - AIG", 0),
        "Parking - AIG": ("Integrated Service Enterprise - AIG", 0),
        "Cafeteria and Parks - AIG": ("Integrated Service Enterprise - AIG", 0),
    }
    for name, (parent, is_group) in expect.items():
        row = frappe.db.get_value("Cost Center", name, ["parent_cost_center", "is_group", "disabled"], as_dict=True)
        assert row, f"missing {name}"
        assert row.parent_cost_center == parent and row.is_group == is_group and row.disabled == 0, f"{name}: {row}"
    for stray in ["Tech - AIG", "Engineering - AIG", "Main - AIG"]:
        assert frappe.db.get_value("Cost Center", stray, "disabled") == 1, f"{stray} should be disabled"
check("Cost Center tree matches brief Section 4 with consistent naming; strays disabled", _cc)

# 6. CC-on-BS enforcement layer
def _enforcement():
    for dt in ["Payment Entry", "Sales Invoice", "Sales Invoice Item",
               "Purchase Invoice", "Purchase Invoice Item", "Journal Entry Account"]:
        assert frappe.get_meta(dt).get_field("cost_center").reqd == 1, f"{dt}.cost_center not reqd"
    guards = frappe.get_all("Server Script", filters={"name": ["like", "AIG - CC Guard%"]}, pluck="name")
    assert len(guards) == 4, f"guards: {guards}"
    comp_cc = frappe.db.get_value("Company", COMPANY, "cost_center")
    assert comp_cc == "Head Office - AIG", f"company default CC: {comp_cc}"
check("Cost Center mandatory (Property Setters + 4 guard scripts) + company default CC set", _enforcement)

# 7. Negative test: with the company default CC temporarily removed, a JE row
# without a cost center must be BLOCKED by the AIG guard.
def _negative_je():
    comp = frappe.get_doc("Company", COMPANY)
    saved_cc = comp.cost_center
    frappe.db.set_value("Company", COMPANY, "cost_center", None)
    try:
        je = frappe.get_doc({
            "doctype": "Journal Entry", "entry_type": "Journal Entry", "company": COMPANY,
            "posting_date": "2026-09-25",
            "accounts": [
                {"account": "Cost of Goods Sold - AIG", "debit_in_account_currency": 100,
                 "cost_center": "Dairy Farm - AIG"},
                {"account": "Cash - AIG", "credit_in_account_currency": 100},  # NO cost center
            ],
        })
        try:
            je.insert()
        except Exception:
            frappe.db.rollback()
            return
        frappe.delete_doc("Journal Entry", je.name, force=True)
        raise AssertionError("JE without any CC coverage was saved - enforcement NOT working!")
    finally:
        frappe.db.set_value("Company", COMPANY, "cost_center", saved_cc)
check("Negative test: JE row without Cost Center is blocked", _negative_je)

# 8. Depreciation inheritance (explicit, from the live test asset)
def _dep():
    rows = frappe.get_all("GL Entry", filters={"voucher_no": "ACC-JV-2026-00001"},
                          fields=["account", "cost_center"])
    assert rows, "depreciation JE GL rows missing"
    for r in rows:
        assert r.cost_center == "Dairy Farm - AIG", f"{r.account} tagged {r.cost_center}"
    accounts = {r.account for r in rows}
    assert "Accumulated Depreciation - AIG" in accounts
check("Depreciation on CC-tagged asset posts CC-tagged Accumulated Depreciation (GL-verified)", _dep)

# 9. AR + Cash tagged to a CC flow to the filtered Balance Sheet (post -> verify -> cancel)
def _ar_flow():
    cust = "AIG AR Test Customer"
    if not frappe.db.exists("Customer", cust):
        frappe.get_doc({"doctype": "Customer", "customer_name": cust, "customer_group": "Commercial",
                        "territory": "Ethiopia", "customer_type": "Company"}).insert()
    je = frappe.get_doc({
        "doctype": "Journal Entry", "entry_type": "Journal Entry", "company": COMPANY,
        "posting_date": "2026-09-25",
        "accounts": [
            {"account": "Debtors - AIG", "party_type": "Customer", "party": cust,
             "debit_in_account_currency": 2000, "cost_center": "Dairy Farm - AIG"},
            {"account": "Sales - AIG", "credit_in_account_currency": 2000,
             "cost_center": "Dairy Farm - AIG"},
        ],
    })
    je.insert(); je.submit(); frappe.db.commit()
    try:
        base = {"company": COMPANY, "filter_based_on": "Fiscal Year", "from_fiscal_year": FY19,
                "to_fiscal_year": FY19, "periodicity": "Yearly", "period": "Yearly",
                "accumulated_in_account_currency": 1}
        rows_f = get_report_result(frappe.get_doc("Report", "Balance Sheet"), {**base, "cost_center": ["Dairy Farm - AIG"]})[1]
        rows_c = get_report_result(frappe.get_doc("Report", "Balance Sheet"), base)[1]
        def val(rows, label):
            for r in rows:
                if r.get("account") == label:
                    return r.get("total") or 0
            return 0
        ar_f, ar_c = val(rows_f, "Accounts Receivable - AIG"), val(rows_c, "Accounts Receivable - AIG")
        assert abs(ar_f - 2000) < 1 and abs(ar_c - 2000) < 1, f"AR filtered={ar_f} consolidated={ar_c}"
    finally:
        je.cancel(); frappe.db.commit()
    frappe.delete_doc("Customer", cust, force=True)
check("AR (Trade Receivable) + Sales tagged to Dairy appear in CC-filtered AND consolidated BS, then cancel cleanly", _ar_flow)

# 10. Budget Variance: consumption per CC (re-verify baseline after earlier test)
def _bvr():
    res = get_report_result(frappe.get_doc("Report", "Budget Variance Report"), {
        "company": COMPANY, "from_fiscal_year": FY19, "to_fiscal_year": FY19,
        "period": "Yearly", "periodicity": "Yearly", "budget_against": "Cost Center"})
    ccs = {r.get("budget_against") for r in res[1]}
    assert {"Dairy Farm - AIG", "Fuel Station - AIG", "Poultry Farm - AIG"} <= ccs, ccs
    assert frappe.db.get_value("Journal Entry", "ACC-JV-2026-00002", "docstatus") == 2
check("Budget Variance Report shows per-Cost-Center budgets; test consumption cancelled cleanly", _bvr)

# 11. Ethiopian date display: display-only, no storage
def _eth():
    for dt in ["Purchase Order", "Journal Entry", "Payment Entry", "Attendance"]:
        cf = frappe.db.get_value("Custom Field", f"{dt}-aig_eth_date_display",
                                 ["fieldtype", "label"], as_dict=True)
        assert cf and cf.fieldtype == "HTML", f"{dt}: {cf}"
    scripts = frappe.get_all("Client Script", filters={"script": ["like", "%aig_eth_date_display%"]},
                             fields=["name", "enabled"])
    assert len(scripts) == 4 and all(s.enabled for s in scripts), scripts
check("Ethiopian-date display: 4 HTML display fields + 4 enabled Client Scripts (no data stored)", _eth)

# 12. Company default bank points at an Asset-root bank account
def _bank():
    b = frappe.db.get_value("Company", COMPANY, "default_bank_account")
    assert b == "Commercial Bank of Ethiopia - AIG"
    assert frappe.db.get_value("Account", b, "root_type") == "Asset"
check("Company default bank account valid and Asset-classified", _bank)

print("\n================= RESULT =================")
fails = [l for s, l in results if s == "FAIL"]
print(f"{len(results) - len(fails)} / {len(results)} PASS")
if fails:
    print("FAILURES:")
    for f in fails:
        print("  -", f)
print("DONE-70")
