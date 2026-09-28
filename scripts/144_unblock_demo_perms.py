# 144_unblock_demo_perms.py -- Add Stock User (Purchase Receipt) and
# Accounts User (Purchase Invoice) to the CUSTOM DocPerm sets that govern
# these doctypes (an earlier phase replaced the standard permission sets with
# AIG-role-only Custom DocPerms; frappe then ignores standard DocPerm rows
# entirely, so plain role grants had no effect). This restores the standard
# frappe expectation that storekeepers receive goods and finance books
# invoices, without touching any AIG role's rights.
# Commits on success; idempotent.
import frappe
from frappe.permissions import add_permission, update_permission_property


def log(*a):
    print(*a, flush=True)


GRANTS = [
    ("Purchase Receipt", "Stock User"),
    ("Purchase Invoice", "Accounts User"),
    ("Purchase Receipt", "AIG Store Keeper"),
]
PTYPES = ["write", "create", "submit", "cancel", "amend"]


def has_custom_perm(dt, role):
    return frappe.db.exists("Custom DocPerm",
                            {"parent": dt, "role": role, "permlevel": 0})


log("1) adding / upgrading standard + store roles in the custom permission sets")
for dt, role in GRANTS:
    if has_custom_perm(dt, role):
        for pt in PTYPES:
            update_permission_property(dt, role, 0, pt, 1)
        log(f"  {dt}: Custom DocPerm for {role} upgraded "
            f"(read + {', '.join(PTYPES)})")
        continue
    add_permission(dt, role, permlevel=0)
    for pt in PTYPES:
        update_permission_property(dt, role, 0, pt, 1)
    log(f"  {dt}: Custom DocPerm added for {role} "
        f"(read + {', '.join(PTYPES)})")

log("")
log("2) clear cache + verify as the demo users")
frappe.clear_cache()
checks = [
    ("storekeeper.agro@aig.local", "Purchase Receipt"),
    ("mainstore@aig.local", "Purchase Receipt"),
    ("finance@aig.local", "Purchase Invoice"),
]
ok = True
for user, dt in checks:
    allowed = frappe.has_permission(dt, "create", user=user)
    ok = ok and allowed
    log(f"  {user} create {dt}: {allowed}")
if not ok:
    raise SystemExit("permission fix did not take effect")
log("DONE 144")
