# 90_hrms_sync.py -- Fix the website-router crash at its root:
# hrms is a registered app (hooks load -> "Job Opening" injected into
# website_generators) but its DocTypes were missing from the DB, so
# _find_matching_document_webview() blew up on every routed path.
# Repair: frappe.model.sync.sync_for("hrms") recreates the missing DocTypes
# (additive; HR tables hold 0 rows), restore the Attendance custom-field
# column for the foundation Ethiopic layer, clear routing caches, verify.

import frappe


def log(*a):
    print(*a, flush=True)


log("STEP 1: sync hrms doctypes")
from frappe.model.sync import sync_for

sync_for("hrms")
log("  sync_for('hrms') done")

log("")
log("STEP 2: verify doctypes now exist")
for dt in ["Job Opening", "Job Applicant", "Attendance", "Leave Application",
           "Leave Type", "HR Settings", "Shift Type", "Expense Claim"]:
    log(f"  {dt}: {'EXISTS' if frappe.db.exists('DocType', dt) else '!! STILL MISSING'}")

log("")
log("STEP 3: Attendance custom-field column (foundation Ethiopic layer)")
if frappe.db.exists("DocType", "Attendance"):
    if not frappe.db.has_column("Attendance", "aig_eth_date_display"):
        try:
            frappe.db.updatedb("Attendance")
            log("  ran db.updatedb('Attendance')")
        except Exception:
            log(f"  !! updatedb failed: {frappe.get_traceback().strip().splitlines()[-1]}")
    log(f"  aig_eth_date_display column: {frappe.db.has_column('Attendance', 'aig_eth_date_display')}")
    cfs = frappe.get_all("Custom Field", filters={"dt": "Attendance"}, pluck="fieldname")
    log(f"  custom fields on Attendance: {cfs}")

log("")
log("STEP 4: data check (sync must NOT have created demo data)")
for dt in ["Job Opening", "Job Applicant", "Attendance", "Employee"]:
    if frappe.db.exists("DocType", dt):
        log(f"  {dt}: {frappe.db.count(dt)} row(s)")

log("")
log("STEP 5: clear caches")
frappe.clear_cache()
frappe.cache.delete_value("doctypes_with_web_view")
log("  cleared")

log("")
log("STEP 6: verify web-view doctype list is fully loadable")
from frappe.website.router import get_doctypes_with_web_view

lst = get_doctypes_with_web_view()
log(f"  list: {list(lst)}")
missing = [d for d in lst if not frappe.db.exists("DocType", d)]
log(f"  missing doctypes in list: {missing or 'none'}")

log("")
if missing:
    log("VERDICT: STILL BROKEN -- see above")
else:
    log("VERDICT: FIXED -- website router list is clean; test http://localhost:8080/login")
