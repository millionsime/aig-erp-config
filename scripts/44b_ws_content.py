# AIG config - step 44b: dump full content JSON of Stock workspace.
import frappe
import json

ws = frappe.db.get_value("Workspace", {"label": "Stock"}, "name")
d = frappe.get_doc("Workspace", ws)
content = d.content
print("RAW content length:", len(content or ""))
try:
    parsed = json.loads(content)
    print("num blocks:", len(parsed))
    for b in parsed[:8]:
        print(json.dumps(b))
except Exception:
    print("content is not JSON or empty:")
    print(repr(content)[:800])
print("\nCONTENT_DONE")
