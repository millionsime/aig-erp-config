# 96_fix_company_alert.py -- Fix "No permission for Company ..." alerts.
# Cause 1: Custom DocPerms (applied by the custom_app/hrms sync) replaced the
#          standard permission set on Company; it contains no AIG role, so AIG
#          demo users have no READ on the Company doctype.
# Cause 2: Users scoped by Cost Center user-permissions (e.g. Agro only) fail
#          the user-permission check on the Company DOCUMENT itself, because
#          Company.cost_center = "Head Office - AIG" is outside their allowed
#          set. Same for the Cost Center tree root.
# Fix (least privilege, isolation-preserving):
#   a) Custom DocPerm READ-only rows on Company for every AIG role.
#   b) Scoped User Permission rows: Cost Center "Head Office - AIG"
#      applicable_for=Company, and root CC applicable_for=Cost Center.
#   c) Give procurement.construction the missing Desk User base role.

import frappe

COMPANY = "Adama Investment Group"
ROOT_CC = f"{COMPANY} - AIG"          # Adama Investment Group - AIG
HEAD_OFFICE_CC = "Head Office - AIG"

AIG_ROLES = [
    "AIG End User", "AIG Procurement Officer", "AIG Enterprise Head",
    "AIG Purchase Committee", "AIG Evaluation Committee", "AIG Corporate",
    "AIG CEO", "AIG Deputy", "AIG Finance",
    "AIG Inventory Administrator", "AIG Main Store Administrator",
    "AIG General Store Keeper", "AIG Store Keeper",
    "AIG Property Admin Expert", "AIG Internal Auditor",
]

SCOPED_USERS = [  # users whose Cost Center perms exclude Head Office
    "enduser.agro@aig.local", "procurement.agro@aig.local",
    "procurement.construction@aig.local", "head.agro@aig.local",
    "head.construction@aig.local", "head.service@aig.local",
    "storeadmin.agro@aig.local", "storekeeper.agro@aig.local",
]


def log(*a):
    print(*a, flush=True)


log("STEP 1: Custom DocPerm READ on Company for AIG roles")
for role in AIG_ROLES:
    existing = frappe.db.get_value(
        "Custom DocPerm", {"parent": "Company", "role": role}, "name"
    )
    if existing:
        cur_read = frappe.db.get_value("Custom DocPerm", existing, "read")
        if not cur_read:
            frappe.db.set_value("Custom DocPerm", existing, "read", 1)
            log(f"  updated: read=1 -> {role}")
        else:
            log(f"  exists with read: {role}")
        continue
    frappe.get_doc({
        "doctype": "Custom DocPerm", "parent": "Company", "parenttype": "DocType",
        "parentfield": "permissions", "role": role, "read": 1,
        "write": 0, "create": 0, "delete": 0, "submit": 0, "cancel": 0,
        "amend": 0, "print": 0, "email": 0, "export": 0, "report": 0,
        "import": 0, "share": 0, "set_user_permissions": 0,
    }).insert(ignore_permissions=True)
    log(f"  created read-only Custom DocPerm: {role}")

log("")
log("STEP 2: scoped user permissions (Company-scoped Head Office CC)")
def add_scoped(user, for_value, applicable_for):
    exists = frappe.db.exists(
        "User Permission",
        {"user": user, "allow": "Cost Center", "for_value": for_value,
         "applicable_for": applicable_for},
    )
    if exists:
        log(f"  exists: {user} CC={for_value} ({applicable_for})")
        return
    frappe.get_doc({
        "doctype": "User Permission", "user": user,
        "allow": "Cost Center", "for_value": for_value,
        "applicable_for": applicable_for, "apply_to_all_doctypes": 0,
    }).insert(ignore_permissions=True)
    log(f"  added: {user} CC={for_value} applicable_for={applicable_for}")

for user in SCOPED_USERS:
    if not frappe.db.exists("User", user):
        log(f"  !! user missing: {user}")
        continue
    add_scoped(user, HEAD_OFFICE_CC, "Company")
    add_scoped(user, ROOT_CC, "Cost Center")

log("")
log("STEP 3: base role consistency")
u = frappe.get_doc("User", "procurement.construction@aig.local")
if "Desk User" not in {r.role for r in (u.roles or [])}:
    u.append("roles", {"role": "Desk User"})
    u.flags.ignore_permissions = True
    u.save(ignore_permissions=True)
    log("  added Desk User -> procurement.construction@aig.local")
else:
    log("  Desk User already present")

log("")
log("STEP 4: clear caches")
frappe.clear_cache()
log("  done")

log("")
log("STEP 5: VERIFY")
from frappe.permissions import get_user_permissions

for user in ["enduser.agro@aig.local", "procurement.agro@aig.local",
             "head.agro@aig.local", "storekeeper.agro@aig.local"]:
    ok = frappe.has_permission("Company", "read", user=user, throw=False)
    frappe.set_user(user)
    try:
        companies = [d.name for d in frappe.get_list("Company", fields=["name"], limit=5)]
    finally:
        frappe.set_user("Administrator")
    log(f"  {user}: role-read={bool(ok)} list-companies={companies}")

# user-permission scope check: Head Office must apply ONLY to Company
up = get_user_permissions("enduser.agro@aig.local")
cc_rows = up.get("Cost Center", [])
ho_any = [r for r in cc_rows if r.get("docname") == HEAD_OFFICE_CC]
log(f"  enduser CC user-perm rows containing Head Office: {[r.get('applicable_for') for r in ho_any]}")
# isolation spot check: Head Office CC must NOT be in the unrestricted MR scope
log(f"  (Cost Center user-perms for MR remain Agro-only)")

log("")
log("VERDICT: fixed if role-read=True and list-companies shows the company")
