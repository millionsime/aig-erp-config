# Check FY state after failed rename (read-only).
for f in frappe.get_all("Fiscal Year", fields=["name", "year_start_date", "year_end_date", "auto_created"]):
    print(f)
print("budget FY refs:", frappe.get_all("Budget", pluck="from_fiscal_year"))
print("DONE")
