# 154_deployment_audit.py -- READ-ONLY: the honest deployment inventory.
# What lives in the site DB (would need fixtures/scripts to travel), what the
# app hooks export (nothing?), site-config time bombs (developer mode,
# server scripts, scheduler), demo-data volume, and specific latent bombs:
# suppliers with a TWC (double-withholding), leaf warehouses without an AIG
# cost center (CC Normalize dead-end), plus the withholder + normalize
# script texts for patching. Creates nothing.
import json

import frappe
from collections import Counter


def log(*a):
    print(*a, flush=True)


COMPANY = "Adama Investment Group"

log("1) app fixtures configured in custom_theme hooks?")
log("  " + json.dumps(frappe.get_hooks("fixtures") or [], default=str))
cfg = frappe.get_common_site_config()
site = frappe.get_site_config()
for k in ["developer_mode", "server_script_enabled"]:
    log(f"  common_site_config[{k}] = {cfg.get(k)!r}")
    log(f"  site_config[{k}] = {site.get(k)!r}")
from frappe.utils.scheduler import is_scheduler_inactive
log(f"  scheduler inactive = {is_scheduler_inactive()}")

log("")
log("2) configuration inventory living ONLY in the site DB")
for dt in ["Custom Field", "Custom DocPerm", "Property Setter",
           "Server Script", "Client Script", "Workflow", "Role",
           "User Permission", "Purchase Taxes and Charges Template",
           "Account", "Cost Center", "Tax Withholding Category"]:
    try:
        log(f"  {dt}: {frappe.db.count(dt)}")
    except Exception as e:
        log(f"  {dt}: n/a ({str(e).splitlines()[0][:60]})")
log(f"  DocType custom=1: {frappe.db.count('DocType', {'custom': 1})}")
log("  custom DocTypes: " + str([r.name for r in frappe.get_all(
    "DocType", filters={"custom": 1}, fields=["name"])]))
log("  workflows: " + str([r.name for r in frappe.get_all(
    "Workflow", fields=["name"])]))
log("  AIG roles: " + str([r.name for r in frappe.get_all(
    "Role", filters={"name": ["like", "AIG%"]}, fields=["name"])]))
log("  server scripts: " + str([(r.name, r.doctype_event, r.disabled)
                                for r in frappe.get_all(
    "Server Script",
    fields=["name", "doctype_event", "disabled"])]))

log("")
log("3) demo/transaction data volume")
for dt in ["Material Request", "Purchase Order", "Purchase Receipt",
           "Purchase Invoice", "Payment Entry", "AIG Committee Signoff"]:
    try:
        rows = frappe.get_all(dt, fields=["workflow_state", "docstatus"],
                              limit_page_length=0)
        c = Counter((r.workflow_state or "(no workflow)") for r in rows)
        log(f"  {dt}: {len(rows)} docs  states={dict(c)}")
    except Exception:
        n = frappe.db.count(dt)
        log(f"  {dt}: {n} docs  (no workflow_state column)")

log("")
log("4) TIME-BOMB scan")
log("  suppliers with tax_withholding_category set (double-withholding risk):")
rows = frappe.get_all("Supplier",
                      filters={"tax_withholding_category": ["is", "set"]},
                      fields=["name", "tax_withholding_category"])
log(f"    {[(r.name, r.tax_withholding_category) for r in rows] or 'none'}")
log("  leaf warehouses without aig_cost_center (CC Normalize dead-end):")
whs = frappe.get_all("Warehouse", filters={"is_group": 0, "company": COMPANY},
                     fields=["name", "aig_cost_center"])
bad = [w.name for w in whs if not w.aig_cost_center]
log(f"    {bad or 'none'} (of {len(whs)} leaf warehouses)")

log("")
log("5) naming series current counters")
for r in frappe.db.sql("select name, current from tabSeries "
                       "order by name limit 30", as_dict=True):
    log(f"  {r.name}: {r.current}")

log("")
log("6) withholder script text (for the TWC-guard patch)")
log(frappe.db.get_value("Server Script",
                        "AIG - Payment Withholding 7.5% + 3%", "script"))

log("")
log("7) MR CC Normalize script text (missing-CC behavior check)")
log(frappe.db.get_value("Server Script", "AIG - MR CC Normalize", "script"))
log("DONE 154")
