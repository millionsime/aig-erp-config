# AIG config - step 43d: validate each print format's Jinja renders with a doc context.
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
    names = frappe.get_all(dt, pluck="name", order_by="creation desc", limit=1)
    if not names:
        print(f"SKIP {fmt}: no {dt}")
        continue
    doc = frappe.get_doc(dt, names[0])
    html = frappe.db.get_value("Print Format", fmt, "html")
    try:
        out = frappe.render_template(html, {"doc": doc, "frappe": frappe})
        good = marker in out
        ok_all = ok_all and good
        print(f"{'PASS' if good else 'WARN'} {fmt}: rendered {len(out)} chars, "
              f"marker '{marker}' {'found' if good else 'MISSING'}")
    except Exception:
        ok_all = False
        print(f"FAIL {fmt}: template error")
        print(traceback.format_exc())

print("\nTEMPLATE_VERIFY_DONE all_ok=", ok_all)
