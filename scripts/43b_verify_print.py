# AIG config - step 43b: verify each AIG print format renders without Jinja errors.
import frappe
import traceback

PAIRS = [
    ("AIG Quality Form", "Quality Inspection", "QUALITY FORM"),
    ("AIG Model 19 Stock Request", "Material Request", "MODEL 19"),
    ("AIG Model 22 Issue Note", "Stock Entry", "MODEL 22"),
    ("AIG Receipt Confirmation", "Material Request", "RECEIPT CONFIRMATION"),
]

ok_all = True
for fmt, dt, marker in PAIRS:
    names = frappe.get_all(dt, filters={}, pluck="name", order_by="creation desc", limit=1)
    if not names:
        print(f"SKIP {fmt}: no {dt} records to render against")
        continue
    name = names[0]
    try:
        html = frappe.get_print(dt, name, print_format=fmt, no_letterhead=True)
        good = bool(html) and (marker in html)
        print(f"{'PASS' if good else 'WARN'} render {fmt} on {dt} {name} "
              f"({len(html)} chars, marker '{marker}' {'found' if marker in html else 'MISSING'})")
        ok_all = ok_all and good
    except Exception:
        ok_all = False
        print(f"FAIL render {fmt} on {dt} {name}")
        print(traceback.format_exc())

print("\nPRINT_VERIFY_DONE all_ok=", ok_all)
