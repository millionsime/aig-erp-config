# 176_enduser_route_verify.py -- VERIFY the end-user-initiated purchase route
# end-to-end, then clean up after itself (self-cleaning like 137/147).
#   C1 end user creates Purchase MR + Submit Purchase Request -> Pending Head Approval
#   C2 negative: end user with exotic type (Manufacture) is blocked by scope guard
#   C3 Enterprise Head Approve -> Pending Store Review
#   C4 Store Admin sets Assigned Officer + Approve & Assign -> Approved
#   C5 officer creates PO <20k from the approved MR -> direct path -> Approved
#   C6 officer raised-MR route unaffected (Submit Request <=750k -> Approved)
import frappe
from frappe.model.workflow import apply_workflow, get_transitions

COMPANY = "Adama Investment Group"
ENDUSER = "enduser.agro@aig.local"
HEAD = "head.agro@aig.local"
OFFICER = "procurement.agro@aig.local"
STORE = "storeadmin.agro@aig.local"
FINANCE = "finance@aig.local"
CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"

CREATED = {"Purchase Order": [], "Material Request": []}

def log(*a):
    print(*a, flush=True)

def as_user(user, fn):
    frappe.set_user(user)
    try:
        return fn()
    finally:
        frappe.set_user("Administrator")

def advance(doctype, name, action, user):
    def run():
        doc = frappe.get_doc(doctype, name)
        apply_workflow(doc, action)
        return frappe.db.get_value(doctype, name, "workflow_state")
    return as_user(user, run)

def make_mr(user, mr_type, item, qty, rate):
    def create():
        mr = frappe.get_doc({
            "doctype": "Material Request", "company": COMPANY,
            "material_request_type": mr_type, "transaction_date": frappe.utils.nowdate(),
            "items": [{"item_code": item, "qty": qty, "uom": "Nos",
                       "schedule_date": frappe.utils.nowdate(), "rate": rate,
                       "warehouse": WH}],
        }).insert(ignore_permissions=True)
        CREATED["Material Request"].append(mr.name)
        return mr.name
    return as_user(user, create)

def cleanup():
    log("")
    log("cleanup: cancelling + deleting every probe document")
    for po in CREATED["Purchase Order"]:
        try:
            frappe.get_doc("Purchase Order", po).cancel()
        except Exception:
            pass
    for mr in CREATED["Material Request"]:
        try:
            frappe.get_doc("Material Request", mr).cancel()
        except Exception:
            pass
    for dt in ["Purchase Order", "Material Request"]:
        for n in CREATED[dt]:
            try:
                frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
            except Exception:
                pass
    frappe.db.commit()
    log("cleanup done")

PASS = 0
FAIL = 0

def check(label, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        log(f"  PASS: {label} {extra}")
    else:
        FAIL += 1
        log(f"  FAIL: {label} {extra}")

try:
    # C1 -- end user initiates a PURCHASE request
    log("C1: end user Purchase MR -> Submit Purchase Request")
    mr1 = make_mr(ENDUSER, "Purchase", "AIG-00001", 2, 1000.0)
    s = advance("Material Request", mr1, "Submit Purchase Request", ENDUSER)
    check("state == Pending Head Approval", s == "Pending Head Approval", f"({mr1}, state={s})")
    ts = as_user(HEAD, lambda: [(t.action for t in get_transitions(frappe.get_doc("Material Request", mr1)))])
    ts = as_user(HEAD, lambda: [t.action for t in get_transitions(frappe.get_doc("Material Request", mr1))])
    check("head sees Approve/Reject", "Approve" in ts and "Reject" in ts, str(ts))

    # C2 -- scope guard blocks exotic types
    log("C2: end user Manufacture type blocked")
    blocked = False
    try:
        make_mr(ENDUSER, "Manufacture", "AIG-00001", 1, 100.0)
    except Exception as e:
        blocked = "may raise" in str(e) or "Purchase" in str(e)
    check("scope guard threw", blocked)

    # C3 -- Enterprise Head approves
    log("C3: head Approve -> Pending Store Review")
    s = advance("Material Request", mr1, "Approve", HEAD)
    check("state == Pending Store Review", s == "Pending Store Review", f"(state={s})")

    # C4 -- store admin assigns purchaser + Approve & Assign
    log("C4: store assigns officer + Approve & Assign -> Approved")
    def assign():
        doc = frappe.get_doc("Material Request", mr1)
        doc.aig_assigned_procurement_officer = OFFICER
        doc.save()
        return True
    as_user(STORE, assign)
    ts = as_user(STORE, lambda: [t.action for t in get_transitions(frappe.get_doc("Material Request", mr1))])
    check("store sees Approve & Assign", "Approve & Assign" in ts, str(ts))
    s = advance("Material Request", mr1, "Approve & Assign", STORE)
    check("state == Approved", s == "Approved", f"(state={s})")
    assigned = frappe.db.get_value("Material Request", mr1, "aig_assigned_procurement_officer")
    check("assignment persisted", assigned == OFFICER, f"({assigned})")

    # C5 -- purchaser creates PO <20k from the approved MR -> direct path
    log("C5: PO 2,000 (<20k) -> Submit for Direct Purchase -> Finance Sign-off")
    def make_po():
        po = frappe.get_doc({
            "doctype": "Purchase Order", "company": COMPANY,
            "supplier": "Blue Nile Trade PLC",
            "transaction_date": frappe.utils.nowdate(), "schedule_date": frappe.utils.nowdate(),
            "currency": "ETB", "aig_cost_center": CC,
            "items": [{"item_code": "AIG-00001", "qty": 2, "rate": 1000.0, "uom": "Nos",
                       "schedule_date": frappe.utils.nowdate(),
                       "material_request": mr1, "warehouse": WH, "cost_center": CC}],
        }).insert(ignore_permissions=True)
        CREATED["Purchase Order"].append(po.name)
        return po.name
    po1 = as_user(OFFICER, make_po)
    s = advance("Purchase Order", po1, "Submit for Direct Purchase", OFFICER)
    check("PO state == Pending Finance Signoff", s == "Pending Finance Signoff", f"(state={s})")
    s = advance("Purchase Order", po1, "Finance Sign-off", FINANCE)
    check("PO state == Approved", s == "Approved", f"(state={s})")

    # C6 -- officer-raised <=750k route unaffected
    log("C6: officer Submit Request (<=750k) still approves directly")
    mr6 = make_mr(OFFICER, "Purchase", "AIG-00001", 3, 800.0)
    frappe.db.set_value("Material Request", mr6, "aig_estimated_total", 2400)
    s = advance("Material Request", mr6, "Submit Request", OFFICER)
    check("officer route -> Approved", s == "Approved", f"(state={s})")

except Exception:
    import traceback
    traceback.print_exc()
    FAIL += 1
finally:
    cleanup()

log("")
log(f"RESULT: {PASS} passed, {FAIL} failed")
if FAIL:
    raise SystemExit(1)
log("OK:176")
