# 174_enduser_purchase_route_probe.py -- READ-ONLY: exact rows of the MR
# workflow (state/action/condition/next_state/doc_status), store-role holders,
# the guard scripts that touch the end-user purchase path, end-user CC scope.
import frappe
import json

def log(*a):
    print(*a, flush=True)

log("=== 1. Workflow 'AIG Stock Request Approval' states ===")
w = frappe.get_doc("Workflow", "AIG Stock Request Approval")
for s in w.states:
    log(f"  state={s.state!r} doc_status={s.doc_status}")

log("")
log("=== 2. Workflow transitions (exact) ===")
for t in w.transitions:
    log(f"  [{t.state}] --{t.action}--> {t.next_state} | allowed={t.allowed} "
        f"| cond={t.condition!r}")

log("")
log("=== 3. Role holders ===")
for role in ["AIG Main Store Administrator", "AIG Enterprise Head", "AIG End User"]:
    holders = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"},
                             pluck="parent", limit=10)
    log(f"  {role}: {holders}")

log("")
log("=== 4. Guard scripts touching the end-user path ===")
for name in ["AIG - MR End User Type Default", "AIG - MR End User Type Guard",
             "AIG - MR Approval Guard", "AIG - MR Request Defaults"]:
    row = frappe.db.get_value("Server Script", name,
                              ["disabled", "script_type", "script"], as_dict=True)
    if row:
        log(f"--- {name} (disabled={row.disabled}, {row.script_type}) ---")
        log(row.script[:1500] if row.script else "(empty)")
    else:
        log(f"--- {name}: NOT FOUND ---")

log("")
log("=== 5. enduser.agro user permissions (CC scope) ===")
for up in frappe.get_all("User Permission", filters={"user": "enduser.agro@aig.local"},
                         fields=["allow", "for_value"], limit=20):
    log(f"  {up.allow}: {up.for_value}")

log("")
log("=== 6. enduser roles ===")
log("  ", frappe.get_all("Has Role", filters={"parent": "enduser.agro@aig.local",
                                          "parenttype": "User"}, pluck="role"))
log("DONE 174")
