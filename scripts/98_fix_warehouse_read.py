# 98_fix_warehouse_read.py -- Same shadowing family as script 96: Warehouse's
# Custom DocPerm set lacks read for non-store AIG roles (End User, Procurement,
# Enterprise Head, Committee, Corporate, CEO, Deputy, Finance, Evaluation),
# so link searches for warehouses fail with "Insufficient Permission for
# Warehouse". Add read-only rows (no write/create/delete), clear cache, verify.

import frappe


def log(*a):
    print(*a, flush=True)


ROLES = [
    "AIG End User", "AIG Procurement Officer", "AIG Enterprise Head",
    "AIG Purchase Committee", "AIG Evaluation Committee", "AIG Corporate",
    "AIG CEO", "AIG Deputy", "AIG Finance",
]

log("STEP 1: read-only Custom DocPerm on Warehouse for AIG viewer roles")
for role in ROLES:
    existing = frappe.db.get_value("Custom DocPerm", {"parent": "Warehouse", "role": role}, "name")
    if existing:
        if not frappe.db.get_value("Custom DocPerm", existing, "read"):
            frappe.db.set_value("Custom DocPerm", existing, "read", 1)
            log(f"  updated read=1: {role}")
        else:
            log(f"  exists: {role}")
        continue
    frappe.get_doc({
        "doctype": "Custom DocPerm", "parent": "Warehouse", "parenttype": "DocType",
        "parentfield": "permissions", "role": role, "read": 1,
        "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
        "amend": 0, "print": 0, "email": 0, "export": 0, "report": 0,
        "import": 0, "share": 0, "set_user_permissions": 0,
    }).insert(ignore_permissions=True)
    log(f"  created read-only: {role}")

log("")
log("STEP 2: clear caches")
frappe.clear_cache()

log("")
log("STEP 3: VERIFY -- role user probes")
role_user = {}
for u in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
    for r in frappe.get_all("Has Role", filters={"parent": u, "parenttype": "User"}, pluck="role"):
        role_user.setdefault(r, u)

all_ok = True
for role in ROLES:
    u = role_user.get(role)
    if not u:
        log(f"  {role}: (no demo user)")
        continue
    wh_ok = frappe.has_permission("Warehouse", "read", user=u, throw=False)
    co_ok = frappe.has_permission("Company", "read", user=u, throw=False)
    it_ok = frappe.has_permission("Item", "read", user=u, throw=False)
    cc_ok = frappe.has_permission("Cost Center", "read", user=u, throw=False)
    ok = wh_ok and co_ok and it_ok and cc_ok
    all_ok = all_ok and ok
    log(f"  {role} ({u}): Warehouse={wh_ok} Company={co_ok} Item={it_ok} CostCenter={cc_ok}")

log("")
log("VERDICT: " + ("ALL GREEN" if all_ok else "!! check the N rows above"))
