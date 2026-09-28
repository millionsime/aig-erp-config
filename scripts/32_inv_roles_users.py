# AIG config - step 32: INVENTORY ROLES + role templates + scoping (config layer).
# Creates the inventory roles, maps them to existing roles where the brief allows,
# provisions clearly-marked DEMO persona users (placeholders - replace with
# authoritative HR data), and applies least-privilege scoping via User Permission
# on Warehouse + Cost Center. Additive & idempotent. NO core edits.
import frappe
import traceback

COMPANY = "Adama Investment Group"
ABBR = "AIG"
DEMO_PASSWORD = "aig2026"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def insert_doc(values, label):
    doc = frappe.get_doc(values)
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"{label}: {doc.name}")
        return doc.name
    except Exception:
        print(f"!! FAILED {label}")
        print(traceback.format_exc())
        return None


# ==================================================================== roles
# New inventory roles (prefixed AIG). Existing roles reused per brief mapping:
#   Enterprise Manager/Director -> "AIG Enterprise Head"
#   Procurement Officer         -> "AIG Procurement Officer"
#   Finance/Inventory Accountant-> "AIG Finance"
#   System Manager/ERP Admin     -> "System Manager"
NEW_ROLES = [
    "AIG Inventory Administrator",
    "AIG Main Store Administrator",
    "AIG General Store Keeper",
    "AIG Store Keeper",
    "AIG Property Admin Expert",
    "AIG End User",
    "AIG Internal Auditor",
]
for r in NEW_ROLES:
    if not frappe.db.exists("Role", r):
        insert_doc({"doctype": "Role", "role_name": r, "desk_access": 1}, f"Role {r}")
    else:
        log("EXISTS", f"Role {r}")

INV_ADMIN = "AIG Inventory Administrator"
MAIN_STORE_ADMIN = "AIG Main Store Administrator"
GEN_STORE_KEEPER = "AIG General Store Keeper"
STORE_KEEPER = "AIG Store Keeper"
PROP_EXPERT = "AIG Property Admin Expert"
END_USER = "AIG End User"
AUDITOR = "AIG Internal Auditor"
ENT_HEAD = "AIG Enterprise Head"

# ============================================ DEMO persona users (PLACEHOLDER)
# FLAG: these @aig.local accounts are reversible demo stand-ins so the workflows
# and acceptance tests are runnable. They are NOT authoritative AIG employees.
# An administrator should replace them (or reassign the roles) with real HR data
# using the role template documented in INVENTORY_GUIDE.txt.
# (email, full name, [roles], [warehouse scopes], [cost-center scopes])
DEMO_USERS = [
    ("inv.admin@aig.local", "Inventory Administrator (demo)",
     [INV_ADMIN], [], []),
    ("mainstore@aig.local", "Main Store Administrator (demo)",
     [MAIN_STORE_ADMIN, STORE_KEEPER], [f"Main Store - {ABBR}"], [f"Head Office - {ABBR}"]),
    ("storeadmin.agro@aig.local", "Store Administrator - Agro (demo)",
     [MAIN_STORE_ADMIN], [f"Dairy Farm Store - {ABBR}", f"Poultry Farm Store - {ABBR}"],
     [f"Agro - {ABBR}", f"Dairy Farm - {ABBR}", f"Poultry Farm - {ABBR}",
      f"Slaughterhouse - {ABBR}", f"Animal Feed Factory - {ABBR}"]),
    ("gsk@aig.local", "General Store Keeper (demo)",
     [GEN_STORE_KEEPER], [], []),
    ("storekeeper.agro@aig.local", "Store Keeper - Agro (demo)",
     [STORE_KEEPER], [f"Dairy Farm Store - {ABBR}", f"Poultry Farm Store - {ABBR}"],
     [f"Agro - {ABBR}", f"Dairy Farm - {ABBR}", f"Poultry Farm - {ABBR}",
      f"Slaughterhouse - {ABBR}", f"Animal Feed Factory - {ABBR}"]),
    ("property.expert@aig.local", "Property Administration Expert (demo)",
     [PROP_EXPERT], [], []),
    ("enduser.agro@aig.local", "End User / Requester - Agro (demo)",
     [END_USER], [],
     [f"Agro - {ABBR}", f"Dairy Farm - {ABBR}", f"Poultry Farm - {ABBR}",
      f"Slaughterhouse - {ABBR}", f"Animal Feed Factory - {ABBR}"]),
    ("auditor@aig.local", "Internal Auditor (demo)",
     [AUDITOR], [], []),
]

for email, full, roles, whs, ccs in DEMO_USERS:
    if not frappe.db.exists("User", email):
        u = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": full,
            "enabled": 1, "user_type": "System User", "new_password": DEMO_PASSWORD,
            "send_welcome_email": 0, "language": "en",
        })
        u.flags.ignore_permissions = True
        u.insert(ignore_permissions=True)
        log("CREATE", f"User {email} ({full}) password={DEMO_PASSWORD} [DEMO PLACEHOLDER]")
    else:
        log("EXISTS", f"User {email}")

    u = frappe.get_doc("User", email)
    u.flags.ignore_permissions = True
    have = {r.role for r in (u.roles or [])}
    for r in roles + ["Desk User"]:
        if r not in have:
            u.append("roles", {"role": r})
            log("ASSIGN", f"Role {r} -> {email}")
    u.save(ignore_permissions=True)

    # warehouse scoping: restrict STOCK MOVEMENTS to assigned stores only.
    # applicable_for="Stock Entry" (apply_to_all_doctypes=0) so it does not
    # AND-filter requests/reports; enterprise isolation is done by cost center below.
    for wh in whs:
        if not frappe.db.exists("Warehouse", wh):
            log("FLAG", f"Warehouse missing for scoping: {wh}")
            continue
        row = frappe.db.get_value("User Permission",
                                  {"user": email, "allow": "Warehouse", "for_value": wh},
                                  "name", as_dict=False)
        if not row:
            insert_doc({"doctype": "User Permission", "user": email, "allow": "Warehouse",
                        "for_value": wh, "apply_to_all_doctypes": 0, "applicable_for": "Stock Entry"},
                       f"UserPermission {email} Warehouse={wh} (Stock Entry only)")
        else:
            frappe.db.set_value("User Permission", row, "apply_to_all_doctypes", 0, update_modified=False)
            frappe.db.set_value("User Permission", row, "applicable_for", "Stock Entry", update_modified=False)
            log("UPDATE", f"UserPermission {email} Warehouse={wh} -> Stock Entry only")
    # cost-center (enterprise) scoping
    for cc in ccs:
        if not frappe.db.exists("Cost Center", cc):
            log("FLAG", f"Cost Center missing for scoping: {cc}")
            continue
        if not frappe.db.exists("User Permission",
                                {"user": email, "allow": "Cost Center", "for_value": cc}):
            insert_doc({"doctype": "User Permission", "user": email, "allow": "Cost Center",
                        "for_value": cc, "apply_to_all_doctypes": 1},
                       f"UserPermission {email} Cost Center={cc}")

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP32_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
