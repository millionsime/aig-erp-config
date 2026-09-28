# Inspect Client Script meta + existing eth fields (read-only).
print("Client Script fieldnames:", [f.fieldname for f in frappe.get_meta("Client Script").fields])
print("autoname:", frappe.get_meta("Client Script").autoname)
print("existing Client Scripts:", frappe.get_all("Client Script", fields=["name", "dt", "view", "enabled"], as_list=True))
print("eth CFs:", frappe.get_all("Custom Field", filters=[["fieldname", "like", "%eth%"]],
                                fields=["name", "dt", "fieldtype", "label"]))
print("DONE")
