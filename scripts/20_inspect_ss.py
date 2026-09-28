import frappe

print("=== SERVER SCRIPTS (AIG) ===")
for s in frappe.get_all("Server Script", filters={"name": ["like", "AIG%"]},
                        fields=["name", "script_type", "reference_doctype", "doctype_event", "disabled"],
                        order_by="name"):
    print(" ", s)

print("\n=== THREE-WAY MATCH SCRIPT BODY ===")
body = frappe.db.get_value("Server Script", "AIG - Payment Three-Way Match", "script")
if body is None:
    # maybe named differently
    for s in frappe.get_all("Server Script", filters={"name": ["like", "AIG%"]}, pluck="name"):
        b = frappe.db.get_value("Server Script", s, "script") or ""
        if "_tol" in b or "tol(" in b or "Three-Way" in b or "three" in b.lower():
            print(f"--- candidate: {s} ---")
            for i, line in enumerate(b.splitlines(), 1):
                print(f"{i:3d}| {line}")
else:
    for i, line in enumerate(body.splitlines(), 1):
        print(f"{i:3d}| {line}")

print("\n=== scan ALL server scripts for '_tol' ===")
for s in frappe.get_all("Server Script", pluck="name"):
    b = frappe.db.get_value("Server Script", s, "script") or ""
    if "_tol" in b:
        print("  HAS _tol ->", s)

print("\n=== demo doc states ===")
for dt, dn in [("Purchase Order", "PUR-ORD-2026-00005"), ("Purchase Order", "PUR-ORD-2026-00006"),
               ("Purchase Order", "PUR-ORD-2026-00004"), ("Payment Entry", "ACC-PAY-2026-00003")]:
    print(" ", dt, dn, frappe.db.get_value(dt, dn, ["workflow_state", "docstatus"]))

print("\nINSPECT_DONE")
