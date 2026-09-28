# AIG config - step 42a: check live state for the Enterprise Head gap.
import frappe

ABBR = "AIG"
print("=== roles exist? ===")
for r in ["AIG Enterprise Head", "AIG Procurement Officer", "AIG Finance",
          "AIG Main Store Administrator", "AIG End User"]:
    print(f"  {r}: {bool(frappe.db.exists('Role', r))}")

print("\n=== head.agro user exists? ===")
U_HEAD = "head.agro@aig.local"
print("  exists:", bool(frappe.db.exists("User", U_HEAD)))
if frappe.db.exists("User", U_HEAD):
    u = frappe.get_doc("User", U_HEAD)
    print("  roles:", [r.role for r in u.roles])
    print("  CC perms:", frappe.get_all("User Permission",
          filters={"user": U_HEAD, "allow": "Cost Center"}, pluck="for_value"))

print("\n=== Custom DocPerm ENT_HEAD on Material Request ===")
row = frappe.db.get_value("Custom DocPerm",
                          {"parent": "Material Request", "role": "AIG Enterprise Head"},
                          "*", as_dict=True)
print("  ", row)

print("\n=== allow_on_submit on key MR custom fields ===")
for f in ["aig_budget_checked", "aig_budget_note", "aig_received_by",
          "aig_received_on", "aig_receipt_confirmed", "aig_receipt_note",
          "aig_issue_reference"]:
    v = frappe.db.get_value("Custom Field", {"dt": "Material Request", "fieldname": f},
                            "allow_on_submit")
    print(f"  MR.{f}: allow_on_submit={v}")

print("\n=== allow_on_submit on key SE custom fields ===")
for f in ["aig_inspected_by", "aig_inspection_notes", "aig_issued_to"]:
    v = frappe.db.get_value("Custom Field", {"dt": "Stock Entry", "fieldname": f},
                            "allow_on_submit")
    print(f"  SE.{f}: allow_on_submit={v}")

print("\nCHECK_DONE")
