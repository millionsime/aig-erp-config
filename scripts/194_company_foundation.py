# Company foundation that every other setup step leans on:
#   1. Fiscal years on the Ethiopian budget cycle (Hamle 1 - Sene 30).
#   2. The cost center tree from aig_hr/data/company_configuration.json
#      (single source of truth: the aig_hr app, not a copy here).
#   3. Company default / round-off / depreciation cost center.
# Idempotent: existing records are left as they are and reported.
import json
import frappe

company = "Adama Investment Group"

# 1. fiscal years (EFY 2018 and 2019, i.e. 2025-26 and 2026-27)
for name, start, end in (
    ("2025-2026 (EFY 2018)", "2025-07-08", "2026-07-07"),
    ("2026-2027 (EFY 2019)", "2026-07-08", "2027-07-07"),
):
    clash = frappe.db.sql("""select name from `tabFiscal Year`
        where year_start_date <= %s and year_end_date >= %s""", (end, start))
    if clash:
        print("fiscal year exists for", start, "->", clash[0][0])
        continue
    fy = frappe.get_doc({"doctype": "Fiscal Year", "year": name,
                         "year_start_date": start, "year_end_date": end,
                         "companies": [{"company": company}]})
    fy.insert(ignore_permissions=True)
    print("created fiscal year", fy.name)

# 2. cost centers
try:
    path = frappe.get_app_path("aig_hr", "data", "company_configuration.json")
except Exception:
    frappe.throw("aig_hr app is not installed in this bench; install it first")
cfg = json.load(open(path))
assert cfg["company"] == company, "company_configuration.json is for another company"

rows = cfg["cost_centers"]
done = set(frappe.get_all("Cost Center", filters={"company": company}, pluck="name"))
pending = [r for r in rows if r["name"] not in done]
while pending:
    batch = [r for r in pending if not r["parent_cost_center"] or r["parent_cost_center"] in done]
    if not batch:
        frappe.throw("cost center parents missing: %s" % [r["name"] for r in pending])
    for r in batch:
        pending.remove(r)
        if not r["parent_cost_center"]:
            print("ROOT cost center missing (ERPNext creates it with the company):", r["name"])
            done.add(r["name"])
            continue
        cc = frappe.get_doc({
            "doctype": "Cost Center", "company": company,
            "cost_center_name": r["cost_center_name"],
            "cost_center_number": r["cost_center_number"] or None,
            "parent_cost_center": r["parent_cost_center"],
            "is_group": r["is_group"], "disabled": r["disabled"],
        })
        cc.insert(ignore_permissions=True)
        if cc.name != r["name"]:
            print("!! created", cc.name, "but expected", r["name"])
        else:
            print("created cost center", cc.name)
        done.add(cc.name)

# 3. company defaults
default_cc = cfg["default_cost_center"]
if frappe.db.exists("Cost Center", default_cc):
    for field in ("cost_center", "round_off_cost_center", "depreciation_cost_center"):
        frappe.db.set_value("Company", company, field, default_cc)
    print("company cost centers ->", default_cc)
else:
    print("!! default cost center missing:", default_cc)

frappe.db.commit()
print("cost centers for company:", frappe.db.count("Cost Center", {"company": company}),
      "(expect", len(rows), ")")
