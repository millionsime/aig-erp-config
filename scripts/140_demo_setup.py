# 140_demo_setup.py -- ONE-TIME demo setup for the purchase-workflow
# walkthrough (commits on success; idempotent - safe to re-run).
#   1) storekeeper.agro  += Stock User   (lets the Store Keeper create the
#      Purchase Receipt / Model 42 stop in the UI demo)
#   2) finance           += Accounts User (lets Finance create the Purchase
#      Invoice for the VAT / withholding demo in the UI)
#   3) demo supplier "Adama Trading PLC" + item "AIG-DEMO-LAPTOP"
#      (qty 10 x 80,000 = 800,000 net -> 920,000 grand -> 60,000 / 24,000
#      withholdings -> 836,000 cash; the exact numbers used in the guide)
import frappe


def log(*a):
    print(*a, flush=True)


def grant(user, role):
    u = frappe.get_doc("User", user)
    if any(r.role == role for r in (u.get("roles") or [])):
        log(f"  {user}: already has {role}")
        return
    u.append("roles", {"role": role})
    u.flags.ignore_permissions = True
    u.save(ignore_permissions=True)
    log(f"  {user}: role granted -> {role}")


log("1) role grants")
grant("storekeeper.agro@aig.local", "Stock User")
grant("finance@aig.local", "Accounts User")

log("")
log("2) demo master data")
SUP = "Adama Trading PLC"
ITEM = "AIG-DEMO-LAPTOP"
if frappe.db.exists("Supplier", SUP):
    log(f"  supplier exists: {SUP}")
else:
    frappe.get_doc({
        "doctype": "Supplier", "supplier_name": SUP,
        "supplier_group": frappe.db.get_single_value("Buying Settings",
                                                     "supplier_group"),
        "company": "Adama Investment Group",
    }).insert(ignore_permissions=True)
    log(f"  supplier created: {SUP}")

if frappe.db.exists("Item", ITEM):
    log(f"  item exists: {ITEM}")
else:
    frappe.get_doc({
        "doctype": "Item", "item_code": ITEM,
        "item_name": "Laptop Pro 15-inch (demo)",
        "item_group": frappe.db.get_value("Item Group", {"is_group": 0},
                                          "name"),
        "stock_uom": "Nos", "is_stock_item": 1, "is_purchase_item": 1,
    }).insert(ignore_permissions=True)
    log(f"  item created: {ITEM}")

log("")
log("3) clear permission cache + verify")
frappe.clear_cache()
for u, role in [("storekeeper.agro@aig.local", "Stock User"),
                ("finance@aig.local", "Accounts User")]:
    log(f"  {u} has {role}: "
        f"{frappe.db.exists('Has Role', {'parenttype': 'User', 'parent': u, 'role': role})}")
log(f"  Purchase Receipt create (storekeeper): "
    f"{frappe.has_permission('Purchase Receipt', 'create', user='storekeeper.agro@aig.local')}")
log(f"  Purchase Invoice create (finance): "
    f"{frappe.has_permission('Purchase Invoice', 'create', user='finance@aig.local')}")
log("DONE 140")
