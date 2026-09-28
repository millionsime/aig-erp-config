# 142_perm_debug.py -- pinpoint WHY doc-level create fails for
# storekeeper/PR and finance/PI while role permissions say yes.
# Dumps User Permission rows and runs frappe.has_permission(debug=True) on a
# NEW (unsaved) doc so the debug log names the exact failing link field.
# Creates nothing.
import frappe

CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"
COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("1) User Permission rows")
for u in ["storekeeper.agro@aig.local", "finance@aig.local",
          "enduser.agro@aig.local", "procurement.agro@aig.local"]:
    rows = frappe.get_all("User Permission",
                          filters={"user": u},
                          fields=["allow", "for_value", "applicable_for",
                                  "hide_descendants"])
    log(f"  {u}:")
    for r in rows:
        log(f"    allow={r.allow} for_value={r.for_value} "
            f"applicable_for={r.applicable_for} hide_desc={r.hide_descendants}")

log("")
log("2) frappe.has_permission(debug=True) on NEW docs")
cases = [
    ("storekeeper.agro@aig.local", "Purchase Receipt", {
        "doctype": "Purchase Receipt", "company": COMPANY, "supplier": "Adama Trading PLC",
        "posting_date": frappe.utils.nowdate(), "cost_center": CC,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 1, "rate": 1000.0,
                   "warehouse": WH, "cost_center": CC}]}),
    ("finance@aig.local", "Purchase Invoice", {
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": "Adama Trading PLC",
        "posting_date": frappe.utils.nowdate(), "cost_center": CC,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 1, "rate": 1000.0,
                   "uom": "Nos", "cost_center": CC}]}),
    ("enduser.agro@aig.local", "Material Request", {
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(), "aig_cost_center": CC,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 1, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 1000.0,
                   "warehouse": WH}]}),
]
for user, dt, payload in cases:
    doc = frappe.get_doc(payload)
    frappe.debug_log = []
    ok = frappe.has_permission(dt, "create", doc=doc, user=user, debug=True)
    log(f"  {user} create {dt}: has_permission={ok}")
    for line in (frappe.debug_log or [])[-25:]:
        log(f"    | {line}")
    frappe.debug_log = []

log("")
log("3) linked doctypes considered for user perms")
from frappe.permissions import get_linked_doctypes
for dt in ["Purchase Receipt", "Purchase Invoice", "Material Request"]:
    log(f"  {dt}: {sorted(set(get_linked_doctypes(dt).values()))}")

log("DONE 142")
