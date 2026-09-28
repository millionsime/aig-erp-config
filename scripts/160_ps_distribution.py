# 160_ps_distribution.py -- READ-ONLY: Property Setter / Custom DocPerm
# distribution by doc_type/parent, to finalize the fixture filters.
import frappe
from collections import Counter


def log(*a):
    print(*a, flush=True)


ps = frappe.get_all("Property Setter", fields=["doc_type"])
log("Property Setter by doc_type:")
for dt, n in Counter(r.doc_type for r in ps).most_common():
    log(f"  {dt}: {n}")

cdp = frappe.get_all("Custom DocPerm", fields=["parent"])
log("")
log("Custom DocPerm by parent:")
for dt, n in Counter(r.parent for r in cdp).most_common():
    log(f"  {dt}: {n}")

cs = frappe.get_all("Client Script", fields=["name", "dt"])
log("")
log("Client Scripts:")
for r in cs:
    log(f"  {r.name} ({r.dt})")
log("DONE 160")
