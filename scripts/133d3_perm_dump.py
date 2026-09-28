# 133d3_perm_dump.py -- READ-ONLY dump of demo user permissions.
import frappe


def log(*a):
    print(*a, flush=True)


USERS = ["procurement.agro@aig.local", "procurement.construction@aig.local",
         "head.agro@aig.local", "head.construction@aig.local",
         "head.service@aig.local", "committee1@aig.local", "committee2@aig.local",
         "committee3@aig.local", "corporate@aig.local", "ceo@aig.local",
         "deputy@aig.local", "finance@aig.local", "enduser.agro@aig.local"]
for u in USERS:
    rows = frappe.get_all("User Permission", filters={"user": u},
                          fields=["allow", "applicable_for", "for_value"])
    log(f"{u}: " + (", ".join(f"allow={r.allow}/appl={r.applicable_for}/{r.for_value}"
                              for r in rows) or "(none)"))
log("")
agro = frappe.get_all("User Permission",
                      filters={"user": "procurement.agro@aig.local",
                               "applicable_for": "Cost Center"},
                      pluck="for_value")
log("agro CCs:", agro)
log("READ-ONLY DUMP DONE")
