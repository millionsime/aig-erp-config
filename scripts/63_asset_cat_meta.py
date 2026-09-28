# Inspect Asset Category child tables (read-only).
cat = frappe.get_meta("Asset Category")
print("Asset Category tables:", [(f.fieldname, f.options) for f in cat.fields if f.fieldtype == "Table"])
opts = {f.fieldname: f.options for f in cat.fields if f.fieldtype == "Table"}
for tn in opts.values():
    print(f"\n{tn} fields:")
    print([f.fieldname for f in frappe.get_meta(tn).fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")])
print("DONE")
