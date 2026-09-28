# 142b_perm_bisect.py -- bisect WHY doc-level create = False:
#   has_controller_permissions / get_role_permissions / has_user_permission
# called directly on NEW unsaved docs. Creates nothing.
import frappe
from frappe.permissions import (get_doc_permissions, get_role_permissions,
                                has_controller_permissions, has_user_permission)

CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"
COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


cases = [
    ("storekeeper.agro@aig.local", "Purchase Receipt", {
        "doctype": "Purchase Receipt", "company": COMPANY,
        "supplier": "Adama Trading PLC",
        "posting_date": frappe.utils.nowdate(), "cost_center": CC,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 1, "rate": 1000.0,
                   "warehouse": WH, "cost_center": CC}]}),
    ("finance@aig.local", "Purchase Invoice", {
        "doctype": "Purchase Invoice", "company": COMPANY,
        "supplier": "Adama Trading PLC",
        "posting_date": frappe.utils.nowdate(), "cost_center": CC,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 1, "rate": 1000.0,
                   "uom": "Nos", "cost_center": CC}]}),
]
for user, dt, payload in cases:
    doc = frappe.get_doc(payload)
    frappe.local.debug_log = []
    log(f"--- {user} / {dt} (NEW doc) ---")
    log(f"  has_controller_permissions(create): "
        f"{has_controller_permissions(doc, 'create', user=user)}")
    rp = get_role_permissions(frappe.get_meta(dt), user=user)
    log(f"  get_role_permissions: create={rp.get('create')} "
        f"if_owner_enabled={rp.get('has_if_owner_enabled')}")
    log(f"  has_user_permission(create): "
        f"{has_user_permission(doc, user, ptype='create')}")
    frappe.local.debug_log = []
    dp = get_doc_permissions(doc, user=user, ptype="create", debug=True)
    log(f"  get_doc_permissions: {dp}")
    for line in (frappe.local.debug_log or [])[-15:]:
        log(f"    | {line}")
    frappe.local.debug_log = []
    log(f"  has_permission(doctype-level): "
        f"{frappe.has_permission(dt, 'create', user=user)}")
    log(f"  has_permission(doc-level): "
        f"{frappe.has_permission(dt, 'create', doc=doc, user=user)}")
log("DONE 142b")
