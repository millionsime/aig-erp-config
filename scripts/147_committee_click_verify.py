# 147_committee_click_verify.py -- VERIFICATION probe for the 146 "click is
# the decision" change (commits only the log; every document created here is
# cancelled + deleted; any crash rolls the whole run back).
#
#   C1  committee member clicks Finalize DIRECTLY (no sign-off row) -> works,
#       their Approve row auto-recorded (the exact UX the demo tripped on)
#   C2  a lone Reject click -> blocked with the TWO-members message, but the
#       member's Reject row IS recorded; second member clicks Reject -> Rejected
#   C3  two manual Rejects block a THIRD (non-rejecting) member's Finalize
#   C4  manual pre-recorded row still works alongside the auto-record

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

RESULTS = []
CREATED = {"Material Request": [], "Purchase Order": [], "CS": []}


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
    def run():
        loaded = frappe.get_doc(doc.doctype, doc.name)
        for t in get_transitions(loaded):
            if target in (t.next_state or ""):
                apply_workflow(loaded, t.action)
                return
        raise SystemExit(f"no transition to {target!r} for {doc.doctype} {doc.name}")

    return as_user(user, run)


def cs_rows(po_name):
    return frappe.get_all("AIG Committee Signoff",
                          filters={"parent_po": po_name},
                          fields=["committee_member", "decision"])


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
        CREATED["Material Request"].append(mr.name)
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
        CREATED["Purchase Order"].append(po.name)
        return po

    po = as_user(OFFICER, create)
    advance(po, "Pending Committee Signoff", OFFICER)
    return po


def cleanup():
    log("")
    log("cleanup")
    for po in CREATED["Purchase Order"]:
        for cs in frappe.get_all("AIG Committee Signoff",
                                 filters={"parent_po": po}, pluck="name"):
            frappe.delete_doc("AIG Committee Signoff", cs,
                              force=True, ignore_permissions=True)
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
            except Exception as e:
                log(f"  !! {dt} {n}: {e}")
    for dt, name in [("Supplier", SUP), ("Item", ITEM)]:
        try:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception:
            pass
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

    mr = make_mr()

    log("")
    log("C1) committee member clicks Finalize DIRECTLY (no sign-off row)")
    po1 = make_po(mr.name, 400000)
    advance(po1, "Pending Enterprise Head Approval", "committee1@aig.local")
    po1.load_from_db()
    rows = cs_rows(po1.name)
    record("C1 direct click -> Pending Enterprise Head Approval",
           po1.workflow_state == "Pending Enterprise Head Approval",
           f"state={po1.workflow_state}")
    record("C1 Approve row auto-recorded for the clicking member",
           len(rows) == 1 and rows[0].committee_member == "committee1@aig.local"
           and rows[0].decision == "Approve", str(rows))
    advance(po1, "Approved", HEAD)
    po1.load_from_db()
    record("C1 head approves -> Approved", po1.workflow_state == "Approved",
           f"state={po1.workflow_state}")

    log("")
    log("C2) rejection = row flow: record 'Reject' row, then click (x2 members)")
    po2 = make_po(mr.name, 400000)
    expect_throw(
        "C2 lone Reject click without a row blocked",
        lambda: advance(po2, "Rejected", "committee1@aig.local"),
        "Record your 'Reject' sign-off first")
    rows = cs_rows(po2.name)
    record("C2 no phantom row left by the bounced click", len(rows) == 0,
           str(rows))
    as_user("committee1@aig.local", lambda: frappe.get_doc({
        "doctype": "AIG Committee Signoff", "parent_po": po2.name,
        "decision": "Reject"}).insert(ignore_permissions=True))
    expect_throw(
        "C2 click with own row but only 1 of 2 rejects blocked",
        lambda: advance(po2, "Rejected", "committee1@aig.local"),
        "one MORE committee member must record")
    as_user("committee2@aig.local", lambda: frappe.get_doc({
        "doctype": "AIG Committee Signoff", "parent_po": po2.name,
        "decision": "Reject"}).insert(ignore_permissions=True))
    advance(po2, "Rejected", "committee1@aig.local")
    po2.load_from_db()
    record("C2 second member's row + click -> Rejected",
           po2.workflow_state == "Rejected", f"state={po2.workflow_state}")

    log("")
    log("C3) two manual Rejects block a THIRD member's Finalize")
    po3 = make_po(mr.name, 400000)
    for m in ["committee1@aig.local", "committee2@aig.local"]:
        as_user(m, lambda: frappe.get_doc({
            "doctype": "AIG Committee Signoff", "parent_po": po3.name,
            "decision": "Reject"}).insert(ignore_permissions=True))
    expect_throw(
        "C3 third member's Finalize blocked while 2 Rejects stand",
        lambda: advance(po3, "Pending Enterprise Head Approval",
                        "committee3@aig.local"),
        "must be Rejected by the committee")

    log("")
    log("C4) manual pre-recorded row + click from the SAME member")
    po4 = make_po(mr.name, 400000)
    as_user("committee2@aig.local", lambda: frappe.get_doc({
        "doctype": "AIG Committee Signoff", "parent_po": po4.name,
        "decision": "Approve"}).insert(ignore_permissions=True))
    advance(po4, "Pending Enterprise Head Approval", "committee2@aig.local")
    rows = cs_rows(po4.name)
    record("C4 manual row reused (no duplicate)",
           len([r for r in rows if r.committee_member == "committee2@aig.local"])
           == 1, str(rows))

    log("")
    fails = [r for r in RESULTS if not r[1]]
    log(f"VERIFY SUMMARY: {len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
    for case, ok, detail in RESULTS:
        log(f"  {'PASS' if ok else 'FAIL'} {case}" + (f" -- {detail}" if detail else ""))
    cleanup()
    if fails:
        raise SystemExit(f"{len(fails)} verification case(s) FAILED")
    residue = [f"{dt} {n}" for dt in ["Purchase Order", "Material Request"]
               for n in CREATED[dt] if frappe.db.exists(dt, n)]
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
