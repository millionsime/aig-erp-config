# 143_roles_debug.py -- decisive: which roles does get_role_permissions SEE,
# and what DocPerm rows exist for PR/PI? Read-only; prints the debug log of
# get_role_permissions (it logs "User has following roles: ...").
import frappe
from frappe.permissions import get_role_permissions


def log(*a):
    print(*a, flush=True)


for user, dt in [("storekeeper.agro@aig.local", "Purchase Receipt"),
                 ("finance@aig.local", "Purchase Invoice")]:
    log(f"--- {user} / {dt} ---")
    log(f"  frappe.get_roles(): {sorted(frappe.get_roles(user))}")
    log(f"  Redis roles: {sorted(frappe.cache().hget('roles', user) or [])}")
    rows = frappe.get_all("Has Role", filters={"parenttype": "User",
                                               "parent": user},
                          fields=["role"])
    log(f"  DB Has Role rows: {[r.role for r in rows]}")
    frappe.local.debug_log = []
    rp = get_role_permissions(frappe.get_meta(dt), user=user, debug=True)
    for line in (frappe.local.debug_log or [])[:10]:
        log(f"    | {line}")
    log(f"  => create={rp.get('create')} submit={rp.get('submit')}")
    frappe.local.debug_log = []

for dt in ["Purchase Receipt", "Purchase Invoice"]:
    perms = frappe.get_all("DocPerm", filters={"parent": dt},
                           fields=["role", "permlevel", "create", "write",
                                   "submit", "read", "if_owner"])
    log(f"{dt} DocPerm rows (DB):")
    for p in perms:
        log(f"  role={p.role} permlevel={p.permlevel} create={p.create} "
            f"write={p.write} submit={p.submit} read={p.read} "
            f"if_owner={p.if_owner}")
    meta = frappe.get_meta(dt)
    log(f"{dt} meta.permissions roles: "
        f"{[(p.role, p.permlevel, int(p.create or 0)) for p in meta.permissions]}")
log("DONE 143")
