# 118_mr_read_bisect.py -- apply_workflow(MR, "Submit Request") as enduser.agro
# failed in get_transitions -> doc.check_permission("read") with a bare
# PermissionError. Bisect WHICH link value fails the doc-level read: create the
# doc, capture frappe message_log (human-readable "Not permitted for ..." rows),
# then clear suspect fields one at a time (warehouse / row cost_center /
# header aig_cost_center / t_warehouse-ish) in memory and re-check. Also dump
# the doc's link values against the user's User Permission rows. Deletes the
# test MR at the end.

import frappe
from frappe.permissions import get_user_permissions

COMPANY = "Adama Investment Group"
ENDUSER = "enduser.agro@aig.local"
ITEM = "AIG-INV-FEED"
WH = "Dairy Farm Store - AIG"


def log(*a):
    print(*a, flush=True)


def check_read(doc, label):
    try:
        doc.check_permission("read")
        log(f"    {label}: READ OK")
    except Exception:
        msgs = [m.get("message") for m in (frappe.local.message_log or [])]
        frappe.local.message_log = []
        tail = frappe.get_traceback().strip().splitlines()
        log(f"    {label}: READ FAIL | msgs={msgs} | {tail[-1] if tail else '?'}")


log("STEP 1: user-permission rows for enduser.agro")
ups = get_user_permissions(ENDUSER)
for allow, rows in sorted(ups.items()):
    for r in rows:
        log(f"  allow={allow} for_value={r.get('docname')} "
            f"applicable_for={r.get('applicable_for')}")

log("")
log("STEP 2: create the rehearsal MR as enduser.agro")
frappe.set_user(ENDUSER)
mr = frappe.new_doc("Material Request")
mr.company = COMPANY
mr.material_request_type = "Material Issue"
mr.schedule_date = frappe.utils.add_days(frappe.utils.nowdate(), 2)
mr.aig_budget_note = "Rehearsal for Saturday demo"
mr.append("items", {"item_code": ITEM, "qty": 2, "schedule_date":
                    mr.schedule_date, "warehouse": WH})
mr.insert()
log(f"  created {mr.name}")

log("")
log("STEP 3: dump the doc's link values")
d = frappe.get_doc("Material Request", mr.name)
log(f"  company={d.company} cost_center={getattr(d, 'cost_center', None)!r} "
    f"aig_cost_center={getattr(d, 'aig_cost_center', None)!r}")
for it in d.items:
    log(f"  row: item={it.item_code} warehouse={it.warehouse!r} "
        f"cost_center={getattr(it, 'cost_center', None)!r} "
        f"aig_cost_center={getattr(it, 'aig_cost_center', None)!r} "
        f"s_warehouse={getattr(it, 's_warehouse', None)!r} "
        f"t_warehouse={getattr(it, 't_warehouse', None)!r}")
log(f"  owner={d.owner} workflow_state={d.workflow_state}")

log("")
log("STEP 4: bisect -- check read, then clear fields one at a time")
d = frappe.get_doc("Material Request", mr.name)
check_read(d, "as-is")

d = frappe.get_doc("Material Request", mr.name)
d.items[0].warehouse = None
check_read(d, "row.warehouse cleared")

d = frappe.get_doc("Material Request", mr.name)
d.items[0].cost_center = None
check_read(d, "row.cost_center cleared")

d = frappe.get_doc("Material Request", mr.name)
d.cost_center = None
check_read(d, "header.cost_center cleared")

d = frappe.get_doc("Material Request", mr.name)
d.aig_cost_center = None
check_read(d, "header.aig_cost_center cleared")

d = frappe.get_doc("Material Request", mr.name)
d.company = None
check_read(d, "header.company cleared")

log("")
log("STEP 5: get_transitions as enduser (fresh doc)")
frappe.set_user(ENDUSER)
d = frappe.get_doc("Material Request", mr.name)
try:
    from frappe.model.workflow import get_transitions
    ts = get_transitions(d)
    log(f"  transitions={[t.action for t in ts]}")
except Exception:
    msgs = [m.get("message") for m in (frappe.local.message_log or [])]
    log(f"  get_transitions FAIL msgs={msgs}")

log("")
log("STEP 6: cleanup")
frappe.set_user("Administrator")
frappe.delete_doc("Material Request", mr.name, ignore_permissions=True, force=True)
log(f"  deleted {mr.name}")
