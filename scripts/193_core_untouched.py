# Proves no ERPNext / Frappe / HRMS DocType was edited in the database
# (developer-mode edits to core). Any hit must move into a Property Setter or
# Custom Field in custom_theme, and the core DocType be reset.
# File-level check, run on the host:
#   docker diff $(<dev.sh or docker compose> ps -q backend) | grep -E 'apps/(frappe|erpnext|hrms)/' | grep -vE '__pycache__|\.pyc$'
import frappe, json, os
from frappe.utils import get_datetime

bad = 0
for app in ("frappe", "erpnext", "hrms"):
    for mod in frappe.get_all("Module Def", filters={"app_name": app}, pluck="name"):
        for dt in frappe.get_all("DocType", filters={"module": mod, "custom": 0}, fields=["name", "modified"]):
            s = frappe.scrub(dt.name)
            p = os.path.join(frappe.get_module_path(mod), "doctype", s, s + ".json")
            if os.path.exists(p):
                fm = json.load(open(p)).get("modified")
                if fm and get_datetime(dt.modified) > get_datetime(fm):
                    print("EDITED IN DB:", app, dt.name)
                    bad += 1
print("core doctypes edited in DB:", bad)
