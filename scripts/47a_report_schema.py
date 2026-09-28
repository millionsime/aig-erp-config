# AIG config - step 47a: inspect Report Builder JSON schema + Report fields.
import frappe
import json

print("=== Report doctype key fields ===")
meta = frappe.get_meta("Report")
for fn in ["report_name", "ref_doctype", "report_type", "json", "module",
           "is_standard", "disabled", "query", "report_script"]:
    df = meta.get_field(fn)
    print(f"  {fn}: {'present' if df else 'ABSENT'}")

print("\n=== existing Report Builder reports (sample json) ===")
rows = frappe.get_all("Report", filters={"report_type": "Report Builder"},
                      fields=["name", "ref_doctype", "json"], limit=3)
if not rows:
    print("  none found")
for r in rows:
    print(f"\n--- {r.name} (ref={r.ref_doctype}) ---")
    print((r.json or "")[:700])

print("\n=== report_type options ===")
df = meta.get_field("report_type")
print(df.options if df else "?")
print("\nSCHEMA_DONE")
