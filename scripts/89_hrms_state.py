# 89_hrms_state.py -- Diagnose the hrms app state: installed-app records,
# presence of its website_generator doctypes (Job Opening/Job Applicant),
# other HR doctypes (Attendance etc.), and hooks. Read-only.

import frappe


def log(*a):
    print(*a, flush=True)


log("INSTALLED APPS")
log(f"  frappe.get_installed_apps(): {frappe.get_installed_apps()}")
for r in frappe.get_all(
    "Installed Application",
    fields=["app_name", "app_version", "git_branch"],
):
    log(f"  Installed Application: {r}")

log("")
log("HOOKS website_generators")
try:
    hooks = frappe.get_hooks("website_generators")
    log(f"  {list(hooks)}")
except Exception:
    log(f"  !! {frappe.get_traceback().strip().splitlines()[-1]}")

log("")
log("DOCTYPE EXISTENCE CHECK")
for dt in [
    "Job Opening", "Job Applicant", "Attendance", "Leave Application",
    "Leave Type", "Employee", "HR Settings", "Shift Type", "Leave Allocation",
    "Appraisal", "Training Event", "Expense Claim",
]:
    log(f"  {dt}: {'EXISTS' if frappe.db.exists('DocType', dt) else 'MISSING'}")

log("")
log("HR-MODULE DOCTYPE COUNT")
rows = frappe.db.sql("select count(*) from `tabDocType` where module = 'HR'")
log(f"  doctypes with module='HR': {rows[0][0]}")

log("")
log("CUSTOM FIELDS / SCRIPTS ON ATTENDANCE (foundation Ethiopic layer)")
if frappe.db.exists("DocType", "Attendance"):
    cfs = frappe.get_all("Custom Field", filters={"dt": "Attendance"}, pluck="fieldname")
    css = frappe.get_all("Client Script", filters={"dt": "Attendance"}, pluck="name")
    log(f"  custom fields: {cfs}")
    log(f"  client scripts: {css}")
else:
    log("  Attendance missing -- foundation Ethiopic layer on Attendance is dangling")

log("")
log("HR DATA ROWS (would be lost by uninstall)")
for dt in ["Employee", "Attendance", "Leave Application", "Leave Allocation"]:
    if frappe.db.exists("DocType", dt):
        log(f"  {dt}: {frappe.db.count(dt)} row(s)")
