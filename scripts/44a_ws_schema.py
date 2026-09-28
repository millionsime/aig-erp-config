# AIG config - step 44a: inspect an existing Workspace's content/links schema.
import frappe
import json

for label in ["Stock", "AIG Procurement"]:
    ws = frappe.db.get_value("Workspace", {"label": label}, "name")
    if not ws:
        print(f"\n### {label}: NOT FOUND")
        continue
    d = frappe.get_doc("Workspace", ws)
    print(f"\n### Workspace {label} (module={d.module}, public={d.public}) ###")
    print("content:", (d.content or "")[:600])
    print("\nlinks child rows:")
    for l in (d.links or []):
        print("  ", {k: l.get(k) for k in ["label", "type", "to", "link_type", "group",
                                           "is_query_report", "report_ref_doctype", "onboard"]})
    print("\nshortcuts child rows:")
    for s in (d.shortcuts or []):
        print("  ", {k: s.get(k) for k in ["label", "type", "link_to", "url", "color", "format"]})
print("\nSCHEMA_DONE")
