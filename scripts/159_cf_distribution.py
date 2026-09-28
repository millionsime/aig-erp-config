# 159_cf_distribution.py -- READ-ONLY: Custom Field distribution by dt and
# prefix, to choose a fixture filter that captures every AIG field without
# importing hrms-owned fields.
import frappe
from collections import Counter


def log(*a):
    print(*a, flush=True)


rows = frappe.get_all("Custom Field", fields=["dt", "fieldname", "module"])
by_dt = Counter(r.dt for r in rows)
log("count by dt:")
for dt, n in by_dt.most_common():
    log(f"  {dt}: {n}")
log("")
log("non-aig-prefixed fieldnames:")
for r in rows:
    if not (r.fieldname.startswith("aig")
            or r.fieldname.startswith("model_42")):
        log(f"  {r.dt}.{r.fieldname} (module={r.module})")
log("")
aig = [r for r in rows if r.fieldname.startswith("aig")
       or r.fieldname.startswith("model_42")]
log(f"AIG-prefixed: {len(aig)} of {len(rows)}")
log("dt list of AIG-prefixed fields: "
    + str(sorted(set(r.dt for r in aig))))
log("DONE 159")
