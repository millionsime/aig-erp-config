# 133d5_perm_pinpoint.py -- ROLLBACK probe v5: exact mini-replica of the
# failing PO transition, with permission diagnostics inline.
import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.permissions import get_doc_permissions
from frappe.utils import nowdate


def log(*a):
    print(*a, flush=True)


COMPANY = "Adama Investment Group"
OFFICER = "procurement.construction@aig.local"
HEAD = "head.construction@aig.local"
SUP = "Probe Supplier Ltd"
ITEM = "AIG-PROBE-ITEM"

whrow = frappe.get_all("Warehouse", filters={"company": COMPANY, "is_group": 0},
                       fields=["name", "aig_cost_center"])
scoped = set(frappe.get_all("User Permission",
                            filters={"user": OFFICER, "allow": "Cost Center",
                                     "for_value": ["!=", "Adama Investment Group - AIG"]},
                            pluck="for_value")) - {"Head Office - AIG"}
cc = wh = None
for r in whrow:
    if r.aig_cost_center and r.aig_cost_center in scoped:
        cc, wh = r.aig_cost_center, r.name
        break
log(f"cc={cc} wh={wh}")

if not frappe.db.exists("Supplier", SUP):
    frappe.get_doc({"doctype": "Supplier", "supplier_name": SUP,
                    "supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group"),
                    "company": COMPANY}).insert(ignore_permissions=True)
if not frappe.db.exists("Item", ITEM):
    frappe.get_doc({"doctype": "Item", "item_code": ITEM, "item_name": "Probe Item",
                    "item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos", "is_stock_item": 1,
                    "is_purchase_item": 1}).insert(ignore_permissions=True)

log("")
log("1) MR as officer -> Endorsed")
frappe.set_user(OFFICER)
try:
    mr = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase", "transaction_date": nowdate(),
        "aig_cost_center": cc, "aig_estimated_total": 800000,
        "items": [{"item_code": ITEM, "qty": 40, "uom": "Nos",
                   "schedule_date": nowdate(), "rate": 20000.0, "warehouse": wh}],
    })
    mr.insert(ignore_permissions=True)
finally:
    frappe.set_user("Administrator")
apply_workflow(mr, "Submit for Endorsement")
frappe.set_user(HEAD)
apply_workflow(mr, "Endorse")
frappe.set_user("Administrator")
log(f"  {mr.name} -> {mr.workflow_state}")

log("")
log("2) PO as officer (identical fields to main probe)")
frappe.set_user(OFFICER)
try:
    po = frappe.get_doc({
        "doctype": "Purchase Order", "company": COMPANY, "supplier": SUP,
        "transaction_date": nowdate(), "schedule_date": nowdate(),
        "currency": "ETB", "aig_cost_center": cc,
        "items": [{"item_code": ITEM, "qty": 40, "rate": 20000.0, "uom": "Nos",
                   "schedule_date": nowdate(), "material_request": mr.name,
                   "warehouse": wh, "cost_center": cc}],
    })
    po.insert(ignore_permissions=True)
    log(f"  {po.name} created state={po.workflow_state}")
except Exception as e:
    import traceback
    log("  PO INSERT FAILED:", repr(e))
    log(traceback.format_exc())
    frappe.db.rollback()
    raise SystemExit(1)
finally:
    frappe.set_user("Administrator")

log("")
log("3) as officer: diagnose the loaded PO")
frappe.set_user(OFFICER)
try:
    loaded = frappe.get_doc("Purchase Order", po.name)
    log("  get_doc_permissions(read):",
        get_doc_permissions(loaded, user=OFFICER, ptype="read"))
    try:
        ts = get_transitions(loaded)
        log("  get_transitions:", [(t.action, t.next_state) for t in ts])
    except Exception as e:
        log("  get_transitions FAILED:", repr(e))
    log("")
    log("4) apply_workflow Submit for Committee Review on the loaded doc")
    try:
        apply_workflow(loaded, "Submit for Committee Review")
        log("  transition OK ->", loaded.workflow_state)
    except Exception as e:
        log("  apply_workflow FAILED:", repr(e))
        import traceback
        log(traceback.format_exc())
finally:
    frappe.set_user("Administrator")

log("")
log("5) rollback")
frappe.db.rollback()
log("ROLLED BACK - pinpoint v5 done")
