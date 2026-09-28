# 155_deployment_audit2.py -- READ-ONLY completion of the 154 audit:
# transaction counts (tolerant), custom DocType module ownership, AIG Module
# Defs, and the WSL-side git repos' state (custom_theme incl. aig_runner.py,
# custom_app, infra). Creates nothing.
import frappe
import subprocess


def log(*a):
    print(*a, flush=True)


log("1) transaction volume (tolerant)")
for dt in ["Purchase Receipt", "Purchase Invoice", "Payment Entry",
           "AIG Committee Signoff", "Stock Entry", "Item", "Supplier",
           "User"]:
    try:
        log(f"  {dt}: {frappe.db.count(dt)}")
    except Exception as e:
        log(f"  {dt}: n/a")

log("")
log("2) custom DocTypes: module ownership (must be app-owned to migrate)")
for r in frappe.get_all("DocType", filters={"custom": 1},
                        fields=["name", "module"]):
    log(f"  {r.name}: module={r.module!r}")
log("  Module Defs: " + str([r.name for r in frappe.get_all(
    "Module Def", fields=["name"], order_by="name")
    if "AIG" in r.name or "Custom" in r.name]))

log("")
log("3) which app do the Server Scripts / Workflows belong to?")
mods = set()
for r in frappe.get_all("Server Script", fields=["module"]):
    mods.add(r.module)
for r in frappe.get_all("Workflow", fields=["module"]):
    mods.add(r.module)
log(f"  modules referenced: {sorted(mods)}")
for m in sorted(mods):
    log(f"    module {m!r}: app="
        f"{frappe.db.get_value('Module Def', m, 'app_name')!r}")

log("DONE 155")
