# Depreciation-window error logs + schedule state (read-only).
from frappe.utils import add_to_date, now_datetime

cutoff = add_to_date(now_datetime(), minutes=-40)
print("cutoff:", cutoff)

print("=== ASSET STATE ===")
print(frappe.db.get_value("Asset", {"asset_name": "AIG CC TEST - Milk Can"},
      ["name", "docstatus", "status", "depr_entry_posting_status", "cost_center"], as_dict=True))

print("\n=== ADS + DS rows ===")
ads = frappe.db.get_value("Asset Depreciation Schedule", {"asset": frappe.db.get_value(
    "Asset", {"asset_name": "AIG CC TEST - Milk Can"}, "name")}, "name")
print("ADS:", ads)
if ads:
    for r in frappe.get_all("Depreciation Schedule", filters={"parent": ads},
                            fields=["idx", "schedule_date", "depreciation_amount", "journal_entry"],
                            limit=5):
        print("  ", r)

print("\n=== ERROR LOGS SINDE WINDOW ===")
logs = frappe.get_all("Error Log", filters={"creation": [">", cutoff]},
                      fields=["name", "creation", "method"], order_by="creation desc", limit=5)
for l in logs:
    d = frappe.get_doc("Error Log", l.name)
    err = d.get("error") or ""
    print("----", l.name, l.creation, "|", getattr(l, "method", ""))
    print(err[:1500])
print("DONE")
