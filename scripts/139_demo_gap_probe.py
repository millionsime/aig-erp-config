# 139_demo_gap_probe.py -- READ-ONLY: committee sign-off + PI creation paths
# for the demo walkthrough. Creates nothing, deletes nothing.
import frappe

USERS = ["committee1@aig.local", "committee2@aig.local",
         "procurement.agro@aig.local", "finance@aig.local"]


def log(*a):
    print(*a, flush=True)


log("AIG Committee Signoff perms:")
for u in USERS:
    p = {pt: frappe.has_permission("AIG Committee Signoff", pt, user=u)
         for pt in ["read", "write", "create", "submit"]}
    log(f"  {u}: " + " ".join(f"{k}={v}" for k, v in p.items()))

log("")
log("Purchase Invoice perm sources:")
log("  docperm rows: " + str(frappe.get_all(
    "DocPerm", filters={"parent": "Purchase Invoice", "create": 1},
    fields=["role"])))
for role in ["Accounts User", "Accounts Manager", "AIG Finance"]:
    log(f"  role exists: {role} = "
        f"{frappe.db.exists('Role', role)}")

log("")
log("Purchase Receipt docperm roles with create: " + str(frappe.get_all(
    "DocPerm", filters={"parent": "Purchase Receipt", "create": 1},
    fields=["role"])))
log("Material Request docperm roles with create: " + str(frappe.get_all(
    "DocPerm", filters={"parent": "Material Request", "create": 1},
    fields=["role"])))

log("")
log("Workflow 'AIG Procurement Approval' transitions:")
for t in frappe.get_all("Workflow Transition",
                        filters={"parent": "AIG Procurement Approval"},
                        fields=["state", "action", "next_state", "allowed",
                                "condition"]):
    log(f"  {t.state} --[{t.action}]--> {t.next_state} (allowed={t.allowed}, "
        f"cond={t.condition})")
