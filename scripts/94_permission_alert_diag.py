# 94_permission_alert_diag.py -- Diagnose the "No permission for ..." alerts
# seen by enduser.agro / procurement.agro: recent Error Log tracebacks,
# each user's User Permissions, and Company doctype read roles.

import frappe


def log(*a):
    print(*a, flush=True)


log("1) RECENT ERROR LOGS (PermissionError / No permission)")
rows = frappe.get_all(
    "Error Log",
    filters={"method": ("like", "%permission%")},
    fields=["name", "method", "creation"],
    order_by="creation desc",
    limit=10,
)
generic = frappe.get_all(
    "Error Log",
    fields=["name", "method", "creation", "error"],
    order_by="creation desc",
    limit=40,
)
shown = 0
for r in generic:
    err = r.error or ""
    if "PermissionError" in err and shown < 6:
        shown += 1
        log(f"--- {r.name} @ {r.creation} method={r.method}")
        # print the most informative lines
        lines = [ln for ln in err.splitlines() if ln.strip()]
        for ln in lines[:6]:
            log(f"    {ln.strip()[:150]}")
        for ln in lines[-8:]:
            log(f"    ...{ln.strip()[:150]}")
if not shown:
    log("  (no PermissionError entries found)")

log("")
log("2) USER PERMISSIONS of affected users")
for user in ["enduser.agro@aig.local", "procurement.agro@aig.local", "head.agro@aig.local", "storeadmin.agro@aig.local"]:
    perms = frappe.get_all(
        "User Permission",
        filters={"user": user},
        fields=["allow", "for_value", "applicable_for", "apply_to_all_doctypes", "is_default"],
        order_by="allow, for_value",
    )
    log(f"  {user}: {len(perms)} permission(s)")
    for p in perms:
        log(f"    allow={p.allow} value={p.for_value} applicable_for={p.applicable_for or 'ALL'} apply_all={p.apply_to_all_doctypes}")

log("")
log("3) COMPANY doctype: who has read?")
log("  docperm roles with read=1:")
for r in frappe.get_all(
    "DocPerm", filters={"parent": "Company", "read": 1}, pluck="role"
):
    log(f"    {r}")
for r in frappe.get_all(
    "Custom DocPerm", filters={"parent": "Company", "read": 1}, pluck="role"
):
    log(f"    [custom] {r}")

log("")
log("4) does session user enduser pass a Company read check?")
from frappe.permissions import has_permission

for user in ["enduser.agro@aig.local", "procurement.agro@aig.local"]:
    ok = has_permission("Company", "read", user=user, throw=False)
    log(f"  {user} read Company: {bool(ok)}")

log("")
log("5) Company.cost_center field (the apply-to-all collision candidate)")
log(f"  Company.cost_center = {frappe.db.get_value('Company', 'Adama Investment Group', 'cost_center')}")
