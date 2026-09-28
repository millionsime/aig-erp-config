# AIG foundation - BUILD C: Cost Center tree standardization.
# Target tree (brief Section 4):
#   Adama Investment Group - AIG (root)
#   ├── Head Office - AIG
#   ├── Agro Enterprise - AIG (group)   [renamed from "Agro - AIG"]
#   │     ├── Dairy/Poultry/Slaughterhouse/Animal Feed Factory (unchanged)
#   ├── Construction Enterprise - AIG (group, NEW)
#   │     └── Construction Projects - AIG (leaf; renamed from group "Construction - AIG")
#   └── Integrated Service Enterprise - AIG (group) [renamed from "Integrated_Service - AIG"]
#         ├── Fuel Station, City Mall, Parking, Cafeteria and Parks (unchanged)
#         └── Garage - AIG (renamed from "Guaraj (Garage) - AIG")
# Stray nodes Tech / Engineering / Main are DISABLED (not deleted - no data loss).
from frappe.model.rename_doc import rename_doc

COMPANY = "Adama Investment Group"
ROOT = "Adama Investment Group - AIG"

def cc_tree():
    rows = frappe.get_all("Cost Center", filters={"disabled": 0},
                          fields=["name", "parent_cost_center", "is_group"], order_by="lft")
    for r in rows:
        print(("  [G] " if r.is_group else "      ") + r.name,
              "<- parent:", r.parent_cost_center)

def gl_snapshot():
    rows = frappe.db.sql("""select ifnull(cost_center,'<none>') cc, count(*) n
                            from `tabGL Entry` group by cost_center""", as_dict=True)
    return {r.cc: r.n for r in rows}

before_gl = gl_snapshot()
print("GL snapshot BEFORE:", before_gl)

# --- 1. Group renames (force=True: allow_rename=0 on core doctype, standard API) ---
for old, new in [
    ("Agro - AIG", "Agro Enterprise - AIG"),
    ("Integrated_Service - AIG", "Integrated Service Enterprise - AIG"),
]:
    if frappe.db.exists("Cost Center", old) and not frappe.db.exists("Cost Center", new):
        rename_doc("Cost Center", old, new, force=True)
        print("RENAMED:", old, "->", new)
    else:
        print("skip rename (already done or missing):", old)

# --- 2. Construction: rename group->leaf name, then create the group above it ---
LEAF_OLD, LEAF_NEW = "Construction - AIG", "Construction Projects - AIG"
GROUP_NEW = "Construction Enterprise - AIG"
if frappe.db.exists("Cost Center", LEAF_OLD) and not frappe.db.exists("Cost Center", LEAF_NEW):
    cc = frappe.get_doc("Cost Center", LEAF_OLD)
    if not cc.is_group:
        frappe.throw("Expected Construction - AIG to be a group before conversion")
    rename_doc("Cost Center", LEAF_OLD, LEAF_NEW, force=True)
    print("RENAMED:", LEAF_OLD, "->", LEAF_NEW)

if not frappe.db.exists("Cost Center", GROUP_NEW):
    g = frappe.new_doc("Cost Center")
    g.cost_center_name = "Construction Enterprise"
    g.parent_cost_center = ROOT
    g.company = COMPANY
    g.is_group = 1
    g.insert()
    print("CREATED group:", g.name)

leaf = frappe.get_doc("Cost Center", LEAF_NEW)
if leaf.parent_cost_center != GROUP_NEW:
    leaf.parent_cost_center = GROUP_NEW
    leaf.save()
    print("RE-PARENTED:", LEAF_NEW, "under", GROUP_NEW)

# --- 3. Guaraj typo rename ---
if frappe.db.exists("Cost Center", "Guaraj (Garage) - AIG") and not frappe.db.exists("Cost Center", "Garage - AIG"):
    rename_doc("Cost Center", "Guaraj (Garage) - AIG", "Garage - AIG", force=True)
    print("RENAMED: Guaraj (Garage) - AIG -> Garage - AIG")

# --- 4. Disable stray nodes (additive-safe: disable, never delete) ---
for stray in ["Tech - AIG", "Engineering - AIG", "Main - AIG"]:
    if frappe.db.exists("Cost Center", stray):
        frappe.db.set_value("Cost Center", stray, "disabled", 1)
        print("DISABLED:", stray)

# --- 5. Re-point construction users' permissions to the enterprise group ---
for user in ["head.construction@aig.local", "procurement.construction@aig.local"]:
    for up in frappe.get_all("User Permission",
                             filters={"user": user, "allow": "Cost Center", "for_value": LEAF_NEW},
                             pluck="name"):
        frappe.db.set_value("User Permission", up, "for_value", GROUP_NEW)
        print("REPOINTED User Permission", up, "->", GROUP_NEW)

# --- 6. Integrity assertions ---
after_gl = gl_snapshot()
print("GL snapshot AFTER :", after_gl)
assert after_gl.get("Dairy Farm - AIG") == before_gl.get("Dairy Farm - AIG"), "Dairy GL rows changed!"

for name in ["Agro Enterprise - AIG", "Integrated Service Enterprise - AIG",
             "Construction Enterprise - AIG", "Construction Projects - AIG", "Garage - AIG",
             "Head Office - AIG", "Dairy Farm - AIG", "Fuel Station - AIG"]:
    assert frappe.db.exists("Cost Center", name), f"missing {name}"
print("All expected cost centers present.")

print("\nPO references after rename:")
for po in frappe.get_all("Purchase Order", fields=["name", "cost_center"]):
    print("  ", po.name, po.cost_center)

print("\nFINAL TREE:")
cc_tree()
print("\nDONE-C")
