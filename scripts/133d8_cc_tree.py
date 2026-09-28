# 133d8_cc_tree.py -- READ-ONLY dump of the Cost Center tree + user scopes.
import frappe


def log(*a):
    print(*a, flush=True)


COMPANY = "Adama Investment Group"
rows = frappe.get_all("Cost Center", filters={"company": COMPANY},
                      fields=["name", "is_group", "lft", "rgt"],
                      order_by="lft")
log("Cost Center tree:")
for r in rows:
    log(f"  {'GROUP' if r.is_group else 'leaf '} {r.name:48s} lft={r.lft} rgt={r.rgt}")

log("")
log("warehouse -> CC mapping (non-group warehouses):")
for r in frappe.get_all("Warehouse", filters={"company": COMPANY, "is_group": 0},
                        fields=["name", "aig_cost_center"], order_by="name"):
    log(f"  {r.name:45s} -> {r.aig_cost_center}")

log("")
log("scoped CCs per demo user (excluding root/HO):")
for u in ["procurement.construction@aig.local", "head.construction@aig.local",
          "procurement.agro@aig.local", "head.agro@aig.local",
          "head.service@aig.local"]:
    vals = frappe.get_all("User Permission",
                          filters={"user": u, "allow": "Cost Center"},
                          pluck="for_value")
    log(f"  {u}: {[v for v in vals if v not in ('Adama Investment Group - AIG', 'Head Office - AIG')]}")

log("")
log("READ-ONLY DUMP DONE")
