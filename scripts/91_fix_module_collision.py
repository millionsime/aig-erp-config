# 91_fix_module_collision.py -- DB-side fix for the HR module collision
# (custom_app claimed module "HR", hijacking hrms's module mapping -> hrms
# DocTypes missing -> website router crash "DocType Job Opening not found").
# File side already renamed (hr -> aig_hr, modules.txt, JSON "module" refs).
# Here: create "AIG HR" Module Def, re-point custom_app-owned records, sync
# custom_app then hrms (recreates Job Opening, Attendance, etc.), restore the
# Attendance Ethiopic custom-field column, clear caches, verify.

import frappe


def log(*a):
    print(*a, flush=True)


log("STEP 1: Module Def 'AIG HR'")
if not frappe.db.exists("Module Def", "AIG HR"):
    frappe.get_doc({
        "doctype": "Module Def",
        "module_name": "AIG HR",
        "app_name": "custom_app",
    }).insert(ignore_permissions=True)
    log("  created Module Def 'AIG HR' (app_name=custom_app)")
else:
    log("  already exists")

log("")
log("STEP 2: re-point custom_app-owned records from module HR -> AIG HR")
for dt, names in [
    ("DocType", ["AIG Service Statement"]),
    ("Workspace", ["AIG HR Expert", "AIG HR Manager"]),
    ("Role", ["AIG HR Expert", "AIG HR Manager", "AIG Enterprise Head"]),
    ("Workflow", ["AIG Service Statement Approval"]),
]:
    has_module_field = "module" in {f.fieldname for f in frappe.get_meta(dt).fields}
    if not has_module_field:
        log(f"  (skip {dt}: no module field)")
        continue
    for n in names:
        if frappe.db.exists(dt, n):
            cur = frappe.db.get_value(dt, n, "module")
            if cur == "HR":
                frappe.db.set_value(dt, n, "module", "AIG HR")
                log(f"  {dt} {n}: HR -> AIG HR")
            else:
                log(f"  {dt} {n}: module already {cur!r}")
        else:
            log(f"  {dt} {n}: not in DB (sync will create)")

log("")
log("STEP 3: sync custom_app (module now AIG HR)")
from frappe.model.sync import sync_for

sync_for("custom_app")
log("  done")

log("")
log("STEP 4: sync hrms (recreates missing HR/Payroll doctypes)")
sync_for("hrms")
log("  done")

log("")
log("STEP 5: verify doctypes exist now")
for dt in ["Job Opening", "Job Applicant", "Attendance", "Leave Application",
           "Leave Type", "HR Settings", "Shift Type", "Expense Claim", "Employee"]:
    log(f"  {dt}: {'EXISTS' if frappe.db.exists('DocType', dt) else '!! STILL MISSING'}")

log("")
log("STEP 6: Attendance Ethiopic custom-field column")
if frappe.db.exists("DocType", "Attendance") and not frappe.db.has_column("Attendance", "aig_eth_date_display"):
    frappe.db.updatedb("Attendance")
    log("  ran db.updatedb('Attendance')")
log(f"  aig_eth_date_display column present: {frappe.db.has_column('Attendance', 'aig_eth_date_display')}")

log("")
log("STEP 7: module mapping check")
from frappe.modules.utils import get_module_app

log(f"  get_module_app('hr') = {get_module_app('hr')}")
log(f"  get_module_app('aig_hr') = {get_module_app('aig_hr')}")

log("")
log("STEP 8: clear caches + verify web-view doctype list")
frappe.clear_cache()
frappe.cache.delete_value("doctypes_with_web_view")
from frappe.website.router import get_doctypes_with_web_view

lst = list(get_doctypes_with_web_view())
log(f"  web-view doctypes: {lst}")
missing = [d for d in lst if not frappe.db.exists("DocType", d)]
log(f"  missing: {missing or 'none'}")

log("")
log("STEP 9: data-integrity check (sync created no demo rows)")
for dt in ["Job Opening", "Job Applicant", "Attendance", "Employee", "Leave Application"]:
    if frappe.db.exists("DocType", dt):
        log(f"  {dt}: {frappe.db.count(dt)} row(s)")

log("")
log("VERDICT: " + ("FIXED -- reload http://localhost:8080/login" if not missing else "STILL BROKEN"))
