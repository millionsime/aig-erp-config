# AIG config - step 43c: inspect stored Print Format html.
import frappe

for fmt in ["AIG Quality Form", "AIG Model 19 Stock Request",
            "AIG Model 22 Issue Note", "AIG Receipt Confirmation"]:
    row = frappe.db.get_value("Print Format", fmt,
                              ["html", "print_format_type", "doc_type", "standard",
                               "disabled", "module"], as_dict=True)
    if not row:
        print(fmt, "-> NOT FOUND")
        continue
    html = row.html or ""
    print(f"\n=== {fmt} ===")
    print("  type:", row.print_format_type, "doc_type:", row.doc_type,
          "standard:", row.standard, "disabled:", row.disabled, "module:", row.module)
    print("  html length:", len(html))
    print("  html head:", repr(html[:120]))
    print("  contains 'MODEL'/'QUALITY'/'RECEIPT':",
          any(m in html for m in ["MODEL", "QUALITY", "RECEIPT"]))
print("\nINSPECT_DONE")
