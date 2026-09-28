# 141_perm_ground_truth.py -- READ-ONLY-ish probe: why does PR-create fail for
# storekeeper and PI-create for finance despite the roles? Attempts one REAL
# draft creation per user (no ignore_permissions) and deletes it afterwards;
# all other checks are read-only.
import frappe
from frappe.permissions import get_role_permissions


def log(*a):
    print(*a, flush=True)


CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"


def real_create_case(label, user, doctype, payload):
    name = None
    try:
        frappe.set_user(user)
        d = frappe.get_doc(payload)
        d.insert()
        name = d.name
        log(f"  {label}: REAL CREATE OK -> {name}")
    except Exception as e:
        log(f"  {label}: REAL CREATE FAILED -> "
            f"{str(e).strip().splitlines()[0][:140]}")
    finally:
        frappe.set_user("Administrator")
        if name:
            try:
                frappe.delete_doc(doctype, name, force=True,
                                  ignore_permissions=True)
                log(f"    (deleted probe doc {name})")
            except Exception as e:
                log(f"    !! delete failed {name}: {e}")


log("hooks: custom has_permission entries for PR / PI")
hooks = frappe.get_hooks("has_permission") or {}
for dt in ["Purchase Receipt", "Purchase Invoice"]:
    log(f"  {dt}: {hooks.get(dt)}")

log("")
log("role permissions snapshot")
for user, dt in [("storekeeper.agro@aig.local", "Purchase Receipt"),
                 ("finance@aig.local", "Purchase Invoice")]:
    rp = get_role_permissions(frappe.get_doc("DocType", dt), user=user)
    log(f"  {user} on {dt}:")
    log(f"    create={rp.get('create')} submit={rp.get('submit')} "
        f"write={rp.get('write')} if_owner={rp.get('if_owner')}")

log("")
log("REAL creation attempts (as the user, no ignore_permissions)")
sup = "Adama Trading PLC"
item = "AIG-DEMO-LAPTOP"
real_create_case(
    "storekeeper -> Purchase Receipt", "storekeeper.agro@aig.local",
    "Purchase Receipt", {
        "doctype": "Purchase Receipt", "company": "Adama Investment Group",
        "supplier": sup, "posting_date": frappe.utils.nowdate(),
        "cost_center": CC,
        "items": [{"item_code": item, "qty": 1, "rate": 1000.0,
                   "warehouse": WH, "cost_center": CC}],
    })
real_create_case(
    "finance -> Purchase Invoice", "finance@aig.local",
    "Purchase Invoice", {
        "doctype": "Purchase Invoice", "company": "Adama Investment Group",
        "supplier": sup, "posting_date": frappe.utils.nowdate(),
        "cost_center": CC,
        "items": [{"item_code": item, "qty": 1, "rate": 1000.0,
                   "uom": "Nos", "cost_center": CC}],
    })
real_create_case(
    "enduser.agro -> Material Request (baseline)", "enduser.agro@aig.local",
    "Material Request", {
        "doctype": "Material Request", "company": "Adama Investment Group",
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(),
        "aig_cost_center": CC,
        "items": [{"item_code": item, "qty": 1, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 1000.0,
                   "warehouse": WH}],
    })
log("")
log("DONE 141")
