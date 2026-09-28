# 138_user_matrix.py -- READ-ONLY demo-user permission matrix for the
# purchase-workflow walkthrough. Creates nothing, deletes nothing.
import frappe

USERS = [
    "enduser.agro@aig.local", "procurement.agro@aig.local",
    "head.agro@aig.local", "storekeeper.agro@aig.local",
    "storeadmin.agro@aig.local", "mainstore@aig.local",
    "inv.admin@aig.local", "finance@aig.local", "deputy@aig.local",
    "corporate@aig.local", "ceo@aig.local",
    "committee1@aig.local", "committee2@aig.local", "committee3@aig.local",
    "auditor@aig.local",
]

DOCTYPES = ["Material Request", "Purchase Order", "Purchase Receipt",
            "Purchase Invoice", "Payment Entry", "Supplier", "Item"]


def log(*a):
    print(*a, flush=True)


log("user".ljust(32) + " ".join(d[:6].rjust(8) for d in DOCTYPES) + "   roles")
for u in USERS:
    cells = []
    for dt in DOCTYPES:
        c = "Y" if frappe.has_permission(dt, "create", user=u) else "-"
        s = "S" if frappe.has_permission(dt, "submit", user=u) else ""
        cells.append((c + s).rjust(8))
    roles = ", ".join(r.role for r in frappe.db.get_all(
        "Has Role", filters={"parenttype": "User", "parent": u},
        fields=["role"]))
    log(u.ljust(32) + " ".join(cells) + "   " + roles)
log("")
log("legend: Y = create, S = submit, - = none (read/submit may differ by doc)")
