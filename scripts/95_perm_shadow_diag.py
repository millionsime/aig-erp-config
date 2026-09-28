# 95_perm_shadow_diag.py -- Enumerate Custom DocPerms (which shadow standard
# DocPerms) introduced by the custom_app HR permission fixtures, compare each
# doctype's custom vs standard role coverage, and test AIG demo roles' access.

import frappe


def log(*a):
    print(*a, flush=True)


AIG_ROLES = [
    "AIG End User", "AIG Procurement Officer", "AIG Enterprise Head",
    "AIG Purchase Committee", "AIG Corporate", "AIG CEO", "AIG Finance",
    "AIG Deputy", "AIG Store Keeper", "AIG Main Store Administrator",
    "AIG General Store Keeper", "AIG Property Admin Expert",
    "AIG Inventory Administrator", "AIG Internal Auditor",
    "AIG Evaluation Committee",
]

log("1) ALL CUSTOM DOCPERMS (grouped by doctype)")
rows = frappe.get_all(
    "Custom DocPerm",
    fields=["parent", "role", "read", "write", "create", "submit", "cancel", "amend"],
    order_by="parent, role",
)
by_dt = {}
for r in rows:
    by_dt.setdefault(r.parent, []).append(r)
for dt in sorted(by_dt):
    roles = [r.role for r in by_dt[dt]]
    log(f"  {dt}: {roles}")

log("")
log("2) STANDARD DOCPERM ROLES per same doctype (now shadowed)")
for dt in sorted(by_dt):
    std = frappe.get_all("DocPerm", filters={"parent": dt}, pluck="role")
    log(f"  {dt}: {sorted(set(std))}")

log("")
log("3) CUSTOM-vs-STANDARD ROLE DELTA (roles losing access)")
for dt in sorted(by_dt):
    std = set(frappe.get_all("DocPerm", filters={"parent": dt}, pluck="role"))
    cus = {r.role for r in by_dt[dt]}
    lost = std - cus
    gained = cus - std
    if lost or gained:
        log(f"  {dt}: lost={sorted(lost)} gained={sorted(gained)}")

log("")
log("4) LIVE ACCESS TEST for each AIG role (read on key doctypes)")
from frappe.permissions import get_doctypes_with_custom_docperm  # noqa

KEY_DT = ["Company", "Account", "Cost Center", "Item", "Warehouse", "Material Request", "Stock Entry"]
# pick one enabled user per role
role_user = {}
for u in frappe.get_all("User", filters={"enabled": 1}, pluck="name"):
    for r in frappe.get_all("Has Role", filters={"parent": u, "parenttype": "User"}, pluck="role"):
        role_user.setdefault(r, u)

for dt in KEY_DT:
    line = []
    for role in AIG_ROLES:
        u = role_user.get(role)
        if not u:
            line.append(f"{role.split()[-1] if False else role}: (no user)")
            continue
        ok = frappe.has_permission(dt, "read", user=u, throw=False)
        line.append(f"{role}={'Y' if ok else 'N'}")
    log(f"  {dt}:")
    for x in line:
        log(f"    {x}")
