# 137_single_approve_verify.py -- VERIFICATION probe for the 136 rule change
# (commits only the log; every document created here is cancelled + deleted,
# and any crash rolls the whole run back).
#
#   V1  PO <=750k, ZERO approvals -> Finalize blocked ("on behalf of all")
#   V2  same PO + ONE Approve     -> Finalize works -> head approves -> Approved
#   V3  PO 800k + ONE Approve     -> Forward to Tender Committee works
#                                 -> Corporate -> CEO -> Approved
#   V4  2 Rejects -> Finalize blocked; Reject action works -> Rejected
#   P   read-only casting report: who may create MR/PO/PR/PI/PE (demo casting)

import frappe
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import nowdate

COMPANY = "Adama Investment Group"
OFFICER = "procurement.agro@aig.local"
HEAD = "head.agro@aig.local"
SUP = "Acceptance Supplier Ltd"
ITEM = "AIG-ACCEPT-ITEM"
CC = "Animal Feed Factory - AIG"
WH = "Animal Feed Plant - AIG"
COMMITTEE = "committee1@aig.local"

RESULTS = []
CREATED = {"MR": [], "PO": [], "CS": []}


def log(*a):
    print(*a, flush=True)


def record(case, ok, detail=""):
    RESULTS.append((case, ok, detail))
    log(f"  {'PASS' if ok else 'FAIL'} {case}" + (f" -- {detail}" if detail else ""))


def expect_throw(case, fn, needle):
    try:
        fn()
        record(case, False, "no exception raised")
    except Exception as e:
        msg = str(e)
        if needle in msg:
            record(case, True, msg.strip().splitlines()[0][:110])
        else:
            record(case, False,
                   f"wrong message: {msg.strip().splitlines()[0][:110]!r} "
                   f"(wanted {needle!r})")


def as_user(user, fn):
    frappe.set_user(user)
    try:
        return fn()
    finally:
        frappe.set_user("Administrator")


def advance(doc, target, user):
    """Apply the first transition as `user` whose next_state contains target."""
    def run():
        loaded = frappe.get_doc(doc.doctype, doc.name)
        for t in get_transitions(loaded):
            if target in (t.next_state or ""):
                apply_workflow(loaded, t.action)
                return
        raise SystemExit(f"no transition to {target!r} for {doc.doctype} {doc.name}")

    return as_user(user, run)


def make_mr():
    def create():
        mr = frappe.get_doc({
            "doctype": "Material Request", "company": COMPANY,
            "material_request_type": "Purchase", "transaction_date": nowdate(),
            "aig_cost_center": CC, "aig_estimated_total": 900000,
            "items": [{"item_code": ITEM, "qty": 10, "uom": "Nos",
                       "schedule_date": nowdate(), "rate": 90000,
                       "warehouse": WH}],
        })
        mr.insert(ignore_permissions=True)
        CREATED["MR"].append(mr.name)
        return mr

    mr = as_user(OFFICER, create)
    advance(mr, "Pending Enterprise Head Endorsement", OFFICER)
    advance(mr, "Endorsed", HEAD)
    return mr


def make_po(mr_name, grand):
    def create():
        po = frappe.get_doc({
            "doctype": "Purchase Order", "company": COMPANY, "supplier": SUP,
            "transaction_date": nowdate(), "schedule_date": nowdate(),
            "currency": "ETB", "aig_cost_center": CC,
            "items": [{"item_code": ITEM, "qty": 10, "rate": grand / 10.0,
                       "uom": "Nos", "schedule_date": nowdate(),
                       "material_request": mr_name, "warehouse": WH,
                       "cost_center": CC}],
        })
        po.insert(ignore_permissions=True)
        CREATED["PO"].append(po.name)
        return po

    po = as_user(OFFICER, create)
    advance(po, "Pending Committee Signoff", OFFICER)
    return po


def signoffs(po_name, decisions):
    for member, decision in decisions:
        def create():
            frappe.get_doc({
                "doctype": "AIG Committee Signoff", "parent_po": po_name,
                "committee_member": member, "decision": decision,
            }).insert(ignore_permissions=True)
            CREATED["CS"].append(po_name)

        as_user(member, create)


def cleanup():
    log("")
    log("cleanup: cancelling + deleting every test document")
    for po in CREATED["PO"]:
        for cs in frappe.get_all("AIG Committee Signoff",
                                 filters={"parent_po": po}, pluck="name"):
            frappe.delete_doc("AIG Committee Signoff", cs,
                              force=True, ignore_permissions=True)
        try:
            frappe.get_doc("Purchase Order", po).cancel()
        except Exception:
            pass
    for mr in CREATED["MR"]:
        try:
            frappe.get_doc("Material Request", mr).cancel()
        except Exception:
            pass
    for dt, names in [("Purchase Order", CREATED["PO"]),
                      ("Material Request", CREATED["MR"])]:
        for n in names:
            try:
                frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
            except Exception as e:
                log(f"  !! could not delete {dt} {n}: {e}")
    for dt, name in [("Supplier", SUP), ("Item", ITEM)]:
        try:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
            log(f"  {dt} deleted")
        except Exception as e:
            log(f"  !! {dt} delete: {e}")
    log("  cleanup done")


def main():
    log("setup: supplier + item")
    if frappe.db.exists("Supplier", SUP):
        frappe.delete_doc("Supplier", SUP, force=True, ignore_permissions=True)
    frappe.get_doc({"doctype": "Supplier", "supplier_name": SUP,
                    "supplier_group": frappe.db.get_single_value(
                        "Buying Settings", "supplier_group"),
                    "company": COMPANY}).insert(ignore_permissions=True)
    if frappe.db.exists("Item", ITEM):
        frappe.delete_doc("Item", ITEM, force=True, ignore_permissions=True)
    frappe.get_doc({"doctype": "Item", "item_code": ITEM,
                    "item_name": "Accept Item",
                    "item_group": frappe.db.get_value(
                        "Item Group", {"is_group": 0}, "name"),
                    "stock_uom": "Nos", "is_stock_item": 1,
                    "is_purchase_item": 1}).insert(ignore_permissions=True)

    log("")
    log("P) casting report: create permissions per demo user (read-only)")
    for dt, users in [("Material Request", ["enduser.agro@aig.local", OFFICER]),
                      ("Purchase Order", [OFFICER]),
                      ("Purchase Receipt", ["storekeeper.agro@aig.local",
                                            "storeadmin.agro@aig.local",
                                            OFFICER]),
                      ("Purchase Invoice", ["finance@aig.local", OFFICER]),
                      ("Payment Entry", ["finance@aig.local"])]:
        for u in users:
            ok = frappe.has_permission(dt, "create", user=u)
            log(f"  {dt} create -- {u}: {ok}")

    log("")
    log("V1+V2) PO 400000: zero approvals blocked, ONE approve finalizes")
    mr = make_mr()
    po = make_po(mr.name, 400000)
    expect_throw(
        "V1 finalize with 0 approvals blocked",
        lambda: advance(po, "Pending Enterprise Head Approval", COMMITTEE),
        "on behalf of all")
    signoffs(po.name, [(COMMITTEE, "Approve")])
    advance(po, "Pending Enterprise Head Approval", COMMITTEE)
    advance(po, "Approved", HEAD)
    po.load_from_db()
    record("V2 ONE approve -> Approved (member decides for all)",
           po.workflow_state == "Approved", f"state={po.workflow_state}")

    log("")
    log("V3) PO 800000: ONE approve carries the bulky chain")
    po3 = make_po(mr.name, 800000)
    signoffs(po3.name, [(COMMITTEE, "Approve")])
    advance(po3, "Pending Corporate Approval", COMMITTEE)
    advance(po3, "Pending CEO Approval", "corporate@aig.local")
    advance(po3, "Approved", "ceo@aig.local")
    po3.load_from_db()
    record("V3 bulky chain with 1 committee approve -> Approved",
           po3.workflow_state == "Approved", f"state={po3.workflow_state}")

    log("")
    log("V4) PO 400000: reject rule unchanged (2 rejects)")
    po4 = make_po(mr.name, 400000)
    signoffs(po4.name, [("committee1@aig.local", "Reject"),
                        ("committee2@aig.local", "Reject")])
    expect_throw(
        "V4 finalize with 2 rejects blocked",
        lambda: advance(po4, "Pending Enterprise Head Approval", COMMITTEE),
        "must be Rejected by the committee")
    advance(po4, "Rejected", COMMITTEE)
    po4.load_from_db()
    record("V4 committee Reject works after 2 rejects",
           po4.workflow_state == "Rejected", f"state={po4.workflow_state}")

    log("")
    fails = [r for r in RESULTS if not r[1]]
    log(f"VERIFY SUMMARY: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
    for case, ok, detail in RESULTS:
        log(f"  {'PASS' if ok else 'FAIL'} {case}"
            + (f" -- {detail}" if detail else ""))
    cleanup()
    if fails:
        raise SystemExit(f"{len(fails)} verification case(s) FAILED")
    residue = [f"{dt} {n}" for dt, names in
               [("Purchase Order", CREATED["PO"]),
                ("Material Request", CREATED["MR"])] for n in names
               if frappe.db.exists(dt, n)]
    if residue:
        raise SystemExit(f"residue left behind: {residue}")
    log("no test residue left - commit persists only the log")


try:
    main()
    log("VERIFY RUN DONE")
except SystemExit:
    frappe.db.rollback()
    raise
except Exception:
    import traceback
    log("!! VERIFY RUN CRASHED:")
    log(traceback.format_exc())
    frappe.db.rollback()
    raise
