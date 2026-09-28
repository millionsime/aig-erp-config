# 133d4_perm_rootcause.py -- READ-ONLY root cause: why scoped users cannot read.
import frappe


def log(*a):
    print(*a, flush=True)


log("1) companies")
for c in frappe.get_all("Company", fields=["name", "abbr"]):
    log(f"  company {c.name!r} abbr={c.abbr!r}")

log("")
log("2) DocPerms on the procurement chain")
for dt in ["Material Request", "Purchase Order", "Purchase Receipt",
           "Purchase Invoice", "Payment Entry"]:
    rows = frappe.get_all("DocPerm", filters={"parent": dt},
                          fields=["role", "read", "write", "create", "submit",
                                  "cancel", "amend", "permlevel"])
    log(f"  {dt}:")
    for r in rows:
        log(f"    {r.role:35s} read={r.read} write={r.write} create={r.create} "
            f"submit={r.submit} cancel={r.cancel} amend={r.amend} lvl={r.permlevel}")

log("")
log("3) as procurement.construction: what fails?")
u = "procurement.construction@aig.local"
frappe.set_user(u)
try:
    log("  has_permission(Material Request, read, no doc):",
        frappe.has_permission("Material Request", "read", user=u))
except Exception as e:
    log("  has_permission threw:", e)
try:
    comp_perm = frappe.permissions.has_user_permission(
        frappe._dict(doctype="Material Request", name="__x", company="Adama Investment Group"), u)
    log("  user-permission check on MR (company=AIG main):", comp_perm)
except Exception as e:
    log("  user-permission check threw:", repr(e))
frappe.set_user("Administrator")

log("")
log("4) role assignments of procurement.construction")
urow = frappe.get_doc("User", u)
log("  roles:", [r.role for r in urow.roles])
log("  enabled:", urow.enabled, " user_type:", urow.user_type)
log("")
log("READ-ONLY DONE")
