# 145_demo_smoke.py -- FULL permission-enforced smoke of the demo path:
# every artifact the walkthrough guide asks a demo user to create is created
# here BY THAT USER with normal permission checks (no ignore_permissions),
# then deleted. Proves the UI walkthrough will not die on permissions.
import frappe
from frappe.model.workflow import apply_workflow
from frappe.utils import nowdate

COMPANY = "Adama Investment Group"
CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"
SUP = "Adama Trading PLC"
ITEM = "AIG-DEMO-LAPTOP"

CREATED = {"Material Request": [], "Purchase Order": [],
           "Purchase Receipt": [], "Purchase Invoice": []}
RESULTS = []


def log(*a):
    print(*a, flush=True)


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    log(f"  {'PASS' if ok else 'FAIL'} {case}" + (f" -- {detail}" if detail else ""))


def as_user(user, fn):
    frappe.set_user(user)
    try:
        return fn()
    finally:
        frappe.set_user("Administrator")


log("1) enduser.agro creates the Material Request (UI path, real perms)")


def mr_create():
    mr = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Purchase", "transaction_date": nowdate(),
        "aig_cost_center": CC, "aig_estimated_total": 900000,
        "items": [{"item_code": ITEM, "qty": 10, "uom": "Nos",
                   "schedule_date": nowdate(), "rate": 80000,
                   "warehouse": WH}],
    })
    mr.insert()
    CREATED["Material Request"].append(mr.name)
    return mr


mr = as_user("enduser.agro@aig.local", mr_create)
record("MR created by enduser.agro", mr.docstatus == 0, mr.name)

log("")
log("2) procurement.agro creates the PO and submits for committee review")


def po_create():
    po = frappe.get_doc({
        "doctype": "Purchase Order", "company": COMPANY, "supplier": SUP,
        "transaction_date": nowdate(), "schedule_date": nowdate(),
        "currency": "ETB", "aig_cost_center": CC,
        "items": [{"item_code": ITEM, "qty": 10, "rate": 80000,
                   "uom": "Nos", "schedule_date": nowdate(),
                   "material_request": mr.name, "warehouse": WH,
                   "cost_center": CC}],
    })
    po.insert()
    CREATED["Purchase Order"].append(po.name)
    return po


po = as_user("procurement.agro@aig.local", po_create)
as_user("procurement.agro@aig.local",
        lambda: apply_workflow(frappe.get_doc("Purchase Order", po.name),
                               "Submit for Committee Review"))
po.load_from_db()
record("PO created + sent to committee by procurement.agro",
       po.workflow_state == "Pending Committee Signoff" and po.docstatus == 1,
       f"state={po.workflow_state} docstatus={po.docstatus}")

log("")
log("3) storekeeper.agro creates the Purchase Receipt draft (Model 42 stop)")


def pr_create():
    pr = frappe.get_doc({
        "doctype": "Purchase Receipt", "company": COMPANY, "supplier": SUP,
        "posting_date": nowdate(), "cost_center": CC,
        "items": [{"item_code": ITEM, "qty": 10, "rate": 80000,
                   "purchase_order": po.name, "warehouse": WH,
                   "cost_center": CC}],
    })
    pr.insert()
    CREATED["Purchase Receipt"].append(pr.name)
    return pr


pr = as_user("storekeeper.agro@aig.local", pr_create)
record("PR draft created by storekeeper.agro", pr.docstatus == 0, pr.name)

log("")
log("4) finance creates the Purchase Invoice with VAT (no submit)")


def pi_create():
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": SUP,
        "posting_date": nowdate(), "taxes_and_charges": "Ethiopia Tax - AIG",
        "cost_center": CC,
        "items": [{"item_code": ITEM, "qty": 10, "rate": 80000,
                   "uom": "Nos", "purchase_order": po.name,
                   "cost_center": CC}],
    })
    pi.insert()
    if pi.taxes_and_charges and not pi.taxes:
        pi.append_taxes_from_master()
        pi.save()
    CREATED["Purchase Invoice"].append(pi.name)
    return pi


pi = as_user("finance@aig.local", pi_create)
record("PI created by finance with VAT 15% (net x 1.15)",
       frappe.utils.flt(pi.grand_total, 2)
       == frappe.utils.flt(pi.net_total * 1.15, 2),
       f"net={pi.net_total} grand={pi.grand_total}")

log("")
log("cleanup: cancelling + deleting smoke documents")
try:
    frappe.get_doc("Purchase Order", po.name).cancel()
except Exception as e:
    log(f"  !! PO cancel: {e}")
for dt in ["Purchase Invoice", "Purchase Receipt", "Purchase Order",
           "Material Request"]:
    for n in CREATED[dt]:
        try:
            frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
            log(f"  deleted {dt} {n}")
        except Exception as e:
            log(f"  !! {dt} {n}: {e}")

fails = [r for r in RESULTS if not r[1]]
log(f"SMOKE SUMMARY: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
if fails:
    raise SystemExit("smoke FAILED")
log("DONE 145 (demo master data supplier + item are kept for the demo)")
