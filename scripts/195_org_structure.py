# Load the AIG organisational structure from the aig_hr app and link each unit
# to its cost center. Needs: aig_hr installed on the site, server scripts
# enabled, and 194_company_foundation.py run first (cost centers).
import json
import frappe

company = "Adama Investment Group"

if "aig_hr" not in frappe.get_installed_apps():
    frappe.throw("aig_hr is not installed on this site: bench --site frontend install-app aig_hr")

from aig_hr.org_import import run as org_import

print("== dry run")
org_import(apply=0)
print("== apply")
org_import(apply=1)

cfg = json.load(open(frappe.get_app_path("aig_hr", "data", "company_configuration.json")))
linked = skipped = 0
for row in cfg["department_cost_centers"]:
    cc = row["cost_center"]
    if not cc:
        skipped += 1
        continue
    if not frappe.db.exists("Department", row["department"]):
        print("!! department missing:", row["department"])
        continue
    if not frappe.db.exists("Cost Center", cc):
        print("!! cost center missing:", cc, "(run 194 first)")
        continue
    frappe.db.set_value("Department", row["department"], "custom_cost_center", cc)
    linked += 1

frappe.db.commit()
print("departments linked to a cost center:", linked, "| left blank by design:", skipped)
print("AIG departments:", frappe.db.count("Department", {"company": company}))
