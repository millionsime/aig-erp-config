# Inspect Server Script meta (read-only) - safe fields only.
print("Server Script fieldnames:")
print([f.fieldname for f in frappe.get_meta("Server Script").fields])
print()
print("Server Script all rows (name only):", frappe.get_all("Server Script", pluck="name"))
print()
one = frappe.get_all("Server Script", pluck="name")
if one:
    d = frappe.get_doc("Server Script", one[0])
    print("first script fields:", {k: v for k, v in d.as_dict().items() if k in
          ("name","script_type","reference_doctype","event","doctype_event","enabled","disabled","api_method","script")})
print("DONE")
