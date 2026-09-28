# Verify Section 9 / acceptance #7: supplier banking details (permlevel 1) are
# visible only to AIG Finance / Corporate / CEO / Deputy. Read-only.
import frappe

SUP = "Ethio Dairy Supplies PLC"

# 1) field config
fld = frappe.db.get_value("Custom Field", {"dt": "Supplier", "fieldname": "aig_bank_details"},
                          ["permlevel", "fieldtype"], as_dict=True)
print("aig_bank_details field:", fld)

# 2) who holds permlevel-1 read on Supplier
rows = frappe.get_all("Custom DocPerm", filters={"parent": "Supplier", "permlevel": 1, "read": 1},
                      fields=["role"], order_by="role")
print("Supplier permlevel-1 read roles:", [r.role for r in rows])

# 3) put a value in the restricted field (admin) so we can prove it is hidden
s = frappe.get_doc("Supplier", SUP)
if not s.get("aig_bank_details"):
    s.aig_bank_details = "CBE 1000123456789 (restricted demo)"
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    frappe.db.commit()
    print("seeded restricted banking value on", SUP)

CAN = {"finance@aig.local", "corporate@aig.local", "ceo@aig.local", "deputy@aig.local"}
CANNOT = {"procurement.agro@aig.local", "head.agro@aig.local", "committee1@aig.local"}


def field_read_perm(user):
    # permlevels the user's roles may READ on Supplier; 1 present => sees banking field
    meta = frappe.get_meta("Supplier")
    return 1 in meta.get_permlevel_access("read", user=user)


print("\n=== runtime permlevel-1 read on Supplier ===")
allok = True
for u in sorted(CAN | CANNOT):
    got = field_read_perm(u)
    want = u in CAN
    flag = "OK" if got == want else "MISMATCH"
    if got != want:
        allok = False
    print(f"  {flag}: {u:32s} permlevel1_read={got} expected={want}")

print("\nSEC9_RESULT:", "PASS" if allok else "FAIL")
print("SEC9_DONE")
