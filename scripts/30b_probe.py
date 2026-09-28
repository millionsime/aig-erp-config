# AIG config - step 30b: quick capability probe for workflow/server-script design.
import frappe

print("=== Server Script doctype_event options ===")
meta = frappe.get_meta("Server Script")
f = meta.get_field("doctype_event")
print(f.options if f else "NO FIELD")

print("\n=== Material Request key fields present? ===")
mr = frappe.get_meta("Material Request")
for fn in ["material_request_type", "schedule_date", "required_by", "set_warehouse",
           "items", "per_ordered", "status", "cost_center", "company", "amended_from"]:
    print(fn, "->", bool(mr.get_field(fn)))
print("MR item fields:", [d.fieldname for d in mr.get_field("items").options and
      frappe.get_meta("Material Request Item").fields][:40])

print("\n=== Material Request material_request_type options ===")
mrt = mr.get_field("material_request_type")
print(mrt.options if mrt else "none")

print("\n=== Stock Entry fields ===")
se = frappe.get_meta("Stock Entry")
for fn in ["stock_entry_type", "purpose", "from_warehouse", "to_warehouse", "items",
           "is_opening", "cost_center", "company", "material_request"]:
    print(fn, "->", bool(se.get_field(fn)))

print("\n=== Stock Entry Detail fields (material_request?) ===")
sed = frappe.get_meta("Stock Entry Detail")
for fn in ["material_request", "material_request_item", "s_warehouse", "t_warehouse",
           "cost_center", "basic_rate", "qty", "item_code"]:
    print(fn, "->", bool(sed.get_field(fn)))

print("\n=== Quality Inspection available? ===")
print("QI doctype:", bool(frappe.db.exists("DocType", "Quality Inspection")))
qi = frappe.get_meta("Quality Inspection") if frappe.db.exists("DocType", "Quality Inspection") else None
if qi:
    for fn in ["inspection_type", "reference_type", "reference_name", "item_code",
               "sample_size", "status", "quality_inspection_template"]:
        print(fn, "->", bool(qi.get_field(fn)))

print("\n=== Stock Entry Type records ===")
print(frappe.get_all("Stock Entry Type", fields=["name", "purpose", "is_standard"]))

print("\n=== existing doc_events hook support (before_workflow_action) ===")
try:
    from frappe.model.workflow import apply_workflow
    print("apply_workflow importable:", True)
except Exception as e:
    print("err", e)

print("\nPROBE_DONE")
