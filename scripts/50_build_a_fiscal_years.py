# AIG foundation - BUILD A: Fiscal Years + Company defaults.
# - Create EC FY2018 record (8 Jul 2025 - 7 Jul 2026).
# - Rename existing FY "2026-27" (8 Jul 2026 - 7 Jul 2027) to an EC-labelled name.
#   Dates are UNCHANGED - it is exactly EC FY2019 under the standard convention.
# - Ensure both FYs are linked to the AIG company.
# - Set Company default bank account (after CoA sanity) and default Cost Center.
COMPANY = "Adama Investment Group"

FY18 = "FY 2018 EC (Jul 2025 - Jul 2026)"
FY19 = "FY 2019 EC (Jul 2026 - Jul 2027)"

if not frappe.db.exists("Fiscal Year", {"year_start_date": "2025-07-08", "year_end_date": "2026-07-07"}):
    fy = frappe.new_doc("Fiscal Year")
    fy.year = FY18
    fy.year_start_date = "2025-07-08"
    fy.year_end_date = "2026-07-07"
    fy.append("companies", {"company": COMPANY})
    fy.insert()
    print("CREATED Fiscal Year:", fy.name)
else:
    print("Fiscal Year for EC2018 already present")

# Existing 2026-27 record: relabel without touching dates or the budget that
# references it. frappe.rename_doc updates the Budget.from_fiscal_year link.
existing = frappe.db.get_value(
    "Fiscal Year",
    {"year_start_date": "2026-07-08", "year_end_date": "2027-07-07"},
    "name",
)
if existing and existing != FY19:
    from frappe.model.rename_doc import rename_doc

    frappe.local.flags.enqueue_after_commit = False
    # force=True: Fiscal Year has allow_rename=0 in core, but rename via the
    # standard API is still required to fix the mislabelled record safely.
    rename_doc("Fiscal Year", existing, FY19, force=True)
    print("RENAMED Fiscal Year", existing, "->", FY19)
else:
    print("FY 2026-27 naming already correct:", existing)

for fy_name in (FY18, FY19):
    d = frappe.get_doc("Fiscal Year", fy_name)
    companies = [c.company for c in (d.get("companies") or [])]
    if COMPANY not in companies:
        d.append("companies", {"company": COMPANY})
        d.save()
        print("LINKED company to", fy_name)
    else:
        print("company already linked:", fy_name)

# CoA sanity for the bank account BEFORE making it the company default
bank = "Commercial Bank of Ethiopia - AIG"
print("CBE account row:", frappe.db.get_value(
    "Account", bank, ["account_name", "parent_account", "root_type", "account_type"], as_dict=True))

# Set company default bank + default cost center
# NOTE v16: the Company field for the default cost center is named
# "cost_center" (label "Default Cost Center"); there is no
# "default_cost_center" fieldname in v16.
c = frappe.get_doc("Company", COMPANY)
c.default_bank_account = bank
if frappe.db.exists("Cost Center", "Head Office - AIG"):
    c.cost_center = "Head Office - AIG"
c.flags.ignore_mandatory = True
c.save()
print("Company defaults set: default_bank_account =", c.default_bank_account,
      "| cost_center (default CC) =", c.cost_center)

print("\nFINAL FY STATE:")
for f in frappe.get_all("Fiscal Year", fields=["name", "year_start_date", "year_end_date"]):
    print("  ", f)
print("\nDONE-A")
