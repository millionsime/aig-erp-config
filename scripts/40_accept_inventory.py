# AIG config - step 40: INVENTORY acceptance / smoke test (config layer, read-mostly).
# Simulates each role and drives the real workflows + server scripts + permissions.
# Creates only clearly-marked AIG-INV demo records. Prints PASS/FAIL per check.
import frappe
import traceback
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
ABBR = "AIG"
ITEM = "AIG-INV-FEED"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
DAIRY_CC = f"Dairy Farm - {ABBR}"
AGRO_CC = f"Agro - {ABBR}"
CONSTRUCTION_CC = "Fuel Station - AIG"  # a valid non-Agro enterprise CC (isolation target)

U_ENDUSER = "enduser.agro@aig.local"
U_STOREADMIN = "storeadmin.agro@aig.local"
U_HEAD = "head.agro@aig.local"
U_KEEPER = "storekeeper.agro@aig.local"
U_GSK = "gsk@aig.local"
U_PROP = "property.expert@aig.local"

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}: {name} {('- ' + detail) if detail else ''}")


def as_admin():
    frappe.set_user("Administrator")


def actual_qty(item, wh):
    as_admin()
    row = frappe.db.sql(
        "select actual_qty from `tabBin` where item_code=%s and warehouse=%s",
        (item, wh), as_dict=True)
    return (row[0].actual_qty if row else 0)


def step(name, fn):
    try:
        return fn()
    except Exception as e:
        print(f"!! EXCEPTION in {name}: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        RESULTS.append((name, False))
        return None


def safe_delete(doctype, name):
    """Cancel-if-submitted then delete a throwaway record, as admin. Never raises.
    Used only for test cleanup so a failed cleanup cannot abort the real checks."""
    as_admin()
    try:
        d = frappe.get_doc(doctype, name)
        if d.docstatus == 1:
            d.flags.ignore_permissions = True
            d.cancel()
            frappe.db.commit()
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
        frappe.db.commit()
    except Exception:
        print(f"   (cleanup: could not fully delete {doctype} {name})")


# ============================================================ setup (as admin)
def setup():
    as_admin()
    if not frappe.db.exists("Item Group", "Consumable Stock"):
        print("!! Consumable Stock item group missing - run step 31")
    if not frappe.db.exists("Item", ITEM):
        it = frappe.get_doc({
            "doctype": "Item", "item_code": ITEM, "item_name": "AIG Demo Dairy Feed",
            "item_group": "Consumable Stock", "stock_uom": "Nos", "is_stock_item": 1,
            "is_purchase_item": 1, "aig_item_classification": "Consumable Stock",
            "item_defaults": [{"company": COMPANY, "default_warehouse": DAIRY_WH}],
        })
        it.flags.ignore_permissions = True
        it.insert(ignore_permissions=True)
        print("### setup: created demo item", ITEM)
    # opening balance 100 via a Material Receipt posted directly (admin seeding)
    start = actual_qty(ITEM, DAIRY_WH)
    if start < 100:
        se = frappe.get_doc({
            "doctype": "Stock Entry", "company": COMPANY, "stock_entry_type": "Material Receipt",
            "purpose": "Material Receipt", "to_warehouse": DAIRY_WH, "cost_center": DAIRY_CC,
            "aig_cost_center": DAIRY_CC, "aig_source_ref": "AIG-OPENING",
            "items": [{"item_code": ITEM, "t_warehouse": DAIRY_WH, "qty": 100 - start,
                       "basic_rate": 10, "cost_center": DAIRY_CC}],
        })
        se.flags.ignore_permissions = True
        se.insert(ignore_permissions=True)
        frappe.db.set_value("Stock Entry", se.name, "workflow_state", "Posted", update_modified=False)
        se.reload()
        se.flags.ignore_permissions = True
        se.submit()
        print("### setup: seeded opening balance to 100")
    as_admin()
    return actual_qty(ITEM, DAIRY_WH)


OPEN = step("setup", setup)
check("setup: opening stock seeded (>=100)", (OPEN or 0) >= 100, f"actual={OPEN}")


# =============================================== T1: request -> approve -> Approved
MR_NAME = {}


def t1_request():
    frappe.set_user(U_ENDUSER)
    mr = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": DAIRY_CC, "aig_purpose_note": "Dairy feed for the week",
        "aig_destination_warehouse": DAIRY_WH,
        "items": [{"item_code": ITEM, "qty": 20, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mr.insert()
    MR_NAME["mr"] = mr.name
    check("T1a: End User can create a Material Issue request", True, mr.name)
    check("T1b: requested_by defaulted to session user", mr.aig_requested_by == U_ENDUSER,
          str(mr.aig_requested_by))
    apply_workflow(mr, "Submit Request")
    frappe.db.commit()
    mr.reload()
    check("T1c: Submit Request -> Pending Store Review",
          mr.workflow_state == "Pending Store Review", mr.workflow_state)
    check("T1d: request is submitted (docstatus 1)", mr.docstatus == 1, str(mr.docstatus))
    as_admin()


step("T1_request", t1_request)


def t1_store_review():
    # budget-check honesty: approving without recording budget must fail (throwaway MR)
    as_admin()
    frappe.set_user(U_ENDUSER)
    mrb = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": DAIRY_CC,
        "items": [{"item_code": ITEM, "qty": 2, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mrb.insert()
    apply_workflow(mrb, "Submit Request")
    frappe.db.commit()
    frappe.set_user(U_STOREADMIN)
    mrb.reload()
    threw = False
    try:
        apply_workflow(mrb, "Approve")
        frappe.db.commit()
    except Exception:
        threw = True
    mrb.reload()
    check("T1e: store review blocked until budget check recorded",
          threw and mrb.workflow_state == "Pending Store Review", mrb.workflow_state)
    safe_delete("Material Request", mrb.name)

    # now record the budget check on the MAIN request and approve
    frappe.set_user(U_STOREADMIN)
    mr = frappe.get_doc("Material Request", MR_NAME["mr"])
    mr.aig_budget_note = "Budget data not available in system - not checked."
    mr.save()
    apply_workflow(mr, "Approve")
    frappe.db.commit()
    mr.reload()
    check("T1f: store review -> Pending Enterprise Approval",
          mr.workflow_state == "Pending Enterprise Approval", mr.workflow_state)
    as_admin()


step("T1_store_review", t1_store_review)


def t1_self_approval():
    # negative: make the store admin the requester, then they must not self-approve
    as_admin()
    mr = frappe.get_doc("Material Request", MR_NAME["mr"])
    frappe.set_user(U_STOREADMIN)
    # craft a fresh request owned by the store admin to test self-approval at head step
    frappe.set_user(U_ENDUSER)
    mr2 = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": DAIRY_CC, "aig_requested_by": U_STOREADMIN,
        "items": [{"item_code": ITEM, "qty": 5, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mr2.insert()
    apply_workflow(mr2, "Submit Request")
    frappe.db.commit()
    # store admin (who is the requester) tries to approve their own request
    frappe.set_user(U_STOREADMIN)
    mr2.reload()
    mr2.aig_budget_checked = 1
    mr2.save()
    threw = False
    try:
        apply_workflow(mr2, "Approve")
        frappe.db.commit()
    except Exception:
        threw = True
    check("T1g: requester cannot approve their own request (self-approval blocked)", threw)
    safe_delete("Material Request", mr2.name)


step("T1_self_approval", t1_self_approval)


def t1_enterprise_approve():
    frappe.set_user(U_HEAD)
    mr = frappe.get_doc("Material Request", MR_NAME["mr"])
    apply_workflow(mr, "Approve")
    frappe.db.commit()
    mr.reload()
    check("T1h: Enterprise Head -> Approved", mr.workflow_state == "Approved", mr.workflow_state)
    as_admin()


step("T1_enterprise_approve", t1_enterprise_approve)


# =============================================== T2: cross-enterprise isolation
def t2_isolation():
    as_admin()
    mr_c = frappe.get_doc({
        "doctype": "Material Request", "company": COMPANY,
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": CONSTRUCTION_CC,
        "items": [{"item_code": ITEM, "qty": 3, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mr_c.flags.ignore_permissions = True
    mr_c.insert(ignore_permissions=True)
    frappe.db.commit()
    cname = mr_c.name

    frappe.set_user(U_ENDUSER)  # scoped to Agro cost centers only
    listed = [d.name for d in frappe.get_list("Material Request", fields=["name"], limit=200)]
    check("T2a: Agro end user does NOT see a Construction request", cname not in listed, cname)
    allowed = frappe.has_permission("Material Request", ptype="read", doc=cname,
                                    user=U_ENDUSER, throw=False)
    check("T2b: Agro end user cannot open the Construction request by name", not allowed)
    as_admin()
    frappe.delete_doc("Material Request", cname, ignore_permissions=True, force=True)
    frappe.db.commit()


step("T2_isolation", t2_isolation)


# =============================================== T3: issue against approved request
def t3_issue():
    before = actual_qty(ITEM, DAIRY_WH)
    frappe.set_user(U_KEEPER)
    se = frappe.get_doc({
        "doctype": "Stock Entry", "company": COMPANY, "stock_entry_type": "Material Issue",
        "purpose": "Material Issue", "from_warehouse": DAIRY_WH, "cost_center": DAIRY_CC,
        "aig_cost_center": DAIRY_CC, "aig_material_request": MR_NAME["mr"],
        "aig_issued_to": U_ENDUSER,
        "items": [{"item_code": ITEM, "s_warehouse": DAIRY_WH, "qty": 20,
                   "cost_center": DAIRY_CC}],
    })
    se.insert()
    sename = se.name
    # raw submit must be blocked by the guard (workflow_state is Draft, not Posted)
    raw_blocked = False
    try:
        se.submit()
        frappe.db.commit()
    except Exception:
        raw_blocked = True
    check("T3a: raw submit of a Stock Entry is blocked by the guard", raw_blocked)
    se.reload()
    apply_workflow(se, "Post Movement")
    frappe.db.commit()
    se.reload()
    check("T3b: issue posts via workflow -> Posted", se.workflow_state == "Posted", se.workflow_state)
    check("T3c: issue docstatus submitted", se.docstatus == 1, str(se.docstatus))
    after = actual_qty(ITEM, DAIRY_WH)
    check("T3d: stock reduced by issued qty (20)", (before - after) == 20, f"{before}->{after}")
    as_admin()
    MR_NAME["issue"] = sename


step("T3_issue", t3_issue)


def t3_over_issue():
    frappe.set_user(U_KEEPER)
    se = frappe.get_doc({
        "doctype": "Stock Entry", "company": COMPANY, "stock_entry_type": "Material Issue",
        "purpose": "Material Issue", "from_warehouse": DAIRY_WH, "cost_center": DAIRY_CC,
        "aig_cost_center": DAIRY_CC, "aig_material_request": MR_NAME["mr"],
        "items": [{"item_code": ITEM, "s_warehouse": DAIRY_WH, "qty": 30,
                   "cost_center": DAIRY_CC}],
    })
    se.insert()
    threw = False
    try:
        apply_workflow(se, "Post Movement")
        frappe.db.commit()
    except Exception:
        threw = True
    check("T3e: over-issue beyond approved request qty is blocked", threw)
    as_admin()
    try:
        frappe.delete_doc("Stock Entry", se.name, ignore_permissions=True, force=True)
        frappe.db.commit()
    except Exception:
        pass


step("T3_over_issue", t3_over_issue)


# =============================================== T4: receiving inspection gate
def t4_receiving():
    start = actual_qty(ITEM, DAIRY_WH)
    frappe.set_user(U_KEEPER)
    se = frappe.get_doc({
        "doctype": "Stock Entry", "company": COMPANY, "stock_entry_type": "Material Receipt",
        "purpose": "Material Receipt", "to_warehouse": DAIRY_WH, "cost_center": DAIRY_CC,
        "aig_cost_center": DAIRY_CC, "aig_source_ref": "DEL-999",
        "items": [{"item_code": ITEM, "t_warehouse": DAIRY_WH, "qty": 40,
                   "basic_rate": 10, "cost_center": DAIRY_CC}],
    })
    se.insert()
    sename = se.name
    apply_workflow(se, "Start Receiving")
    frappe.db.commit()
    se.reload()
    check("T4a: receipt in Pending Inspection is NOT posted (no stock yet)",
          se.docstatus == 0 and actual_qty(ITEM, DAIRY_WH) == start, se.workflow_state)
    # Record Inspection without a Quality Inspection must be blocked
    gate_blocked = False
    try:
        apply_workflow(se, "Record Inspection")
        frappe.db.commit()
    except Exception:
        gate_blocked = True
    check("T4b: cannot advance past inspection without a submitted Quality Form", gate_blocked)
    # create + submit the Quality Inspection (Quality Form)
    se.reload()
    qi = frappe.get_doc({
        "doctype": "Quality Inspection", "inspection_type": "Incoming",
        "reference_type": "Stock Entry", "reference_name": sename,
        "item_code": ITEM, "sample_size": 40, "status": "Accepted",
        "inspected_by": U_KEEPER, "remarks": "AIG demo receiving inspection",
    })
    qi.insert()
    qi.submit()
    frappe.db.commit()
    check("T4c: Quality Form (Quality Inspection) submitted", qi.docstatus == 1, qi.name)
    apply_workflow(se, "Record Inspection")
    frappe.db.commit()
    se.reload()
    check("T4d: after Quality Form, -> Pending GSK Approval",
          se.workflow_state == "Pending GSK Approval", se.workflow_state)

    frappe.set_user(U_GSK)
    se.reload()
    apply_workflow(se, "Approve")
    frappe.db.commit()
    se.reload()
    check("T4e: GSK approve -> Pending Property Assignment",
          se.workflow_state == "Pending Property Assignment", se.workflow_state)

    frappe.set_user(U_PROP)
    se.reload()
    apply_workflow(se, "Assign Bins")
    frappe.db.commit()
    se.reload()
    check("T4f: Property Expert assigns bins -> Pending Posting (no stock yet)",
          se.workflow_state == "Pending Posting" and se.docstatus == 0, se.workflow_state)

    frappe.set_user(U_GSK)
    se.reload()
    apply_workflow(se, "Post Receipt")
    frappe.db.commit()
    se.reload()
    check("T4g: GSK posts -> Posted", se.workflow_state == "Posted", se.workflow_state)
    after = actual_qty(ITEM, DAIRY_WH)
    check("T4h: accepted qty added to stock (+40)", (after - start) == 40, f"{start}->{after}")
    as_admin()


step("T4_receiving", t4_receiving)


# =============================================== T5: reports respect enterprise scope
def t5_reports_scoped():
    as_admin()
    allowed = set(frappe.get_all("User Permission",
                  filters={"user": U_ENDUSER, "allow": "Cost Center"}, pluck="for_value"))
    frappe.set_user(U_ENDUSER)
    rows = frappe.get_list("Material Request",
                           fields=["name", "aig_cost_center"], limit=500)
    leaked = [r.name for r in rows if r.aig_cost_center and r.aig_cost_center not in allowed]
    check("T5a: scoped list/report query returns only the user's enterprise cost centers",
          not leaked, f"leaked={leaked[:3]}")
    as_admin()
    rep = frappe.db.get_value("Report", "AIG Outstanding Stock Requests",
                              ["report_type", "ref_doctype"], as_dict=True)
    check("T5b: AIG saved report exists (Report Builder on Material Request)",
          bool(rep) and rep.report_type == "Report Builder"
          and rep.ref_doctype == "Material Request")


step("T5_reports_scoped", t5_reports_scoped)


# =============================================== summary
as_admin()
passed = sum(1 for _, ok in RESULTS if ok)
total = len(RESULTS)
print("\n================ INVENTORY ACCEPTANCE ================")
for n, ok in RESULTS:
    print(f"  {'PASS' if ok else 'FAIL'}  {n}")
print(f"RESULT: {passed}/{total} PASS")
print("ACCEPT_DONE")


def run():
    frappe.db.commit()
    return f"{passed}/{total}"
