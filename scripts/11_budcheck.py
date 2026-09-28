print("=== Budget is_submittable? ===")
print(frappe.get_meta("Budget").is_submittable)
print("=== use_legacy_budget_controller ===")
print(frappe.get_single_value("Accounts Settings", "use_legacy_budget_controller"))
print("=== BUDGETS docstatus ===")
for b in frappe.get_all("Budget", fields=["name", "cost_center", "account", "budget_amount",
                                          "docstatus", "from_fiscal_year", "to_fiscal_year",
                                          "budget_start_date", "budget_end_date",
                                          "applicable_on_purchase_order",
                                          "action_if_annual_budget_exceeded_on_po"]):
    print(b)
print("BUDGETCHK_DONE")
