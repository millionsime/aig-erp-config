# 180_cal_boot_debug.py -- READ-ONLY: find why /app 500s after the calendar
# app install. Import every hook target the site will load.
import frappe
import traceback

def log(*a):
    print(*a, flush=True)

log("installed apps:", frappe.get_installed_apps())
log("boot_session hooks:", frappe.get_hooks("boot_session"))
for path in frappe.get_hooks("boot_session") or []:
    try:
        frappe.get_attr(path)
        log("  OK import:", path)
    except Exception:
        log("  FAIL import:", path)
        traceback.print_exc()

log("jinja hooks:", frappe.get_hooks("jinja_methods"))
for path in (frappe.get_hooks("jinja_methods") or {}).values():
    p = path[0] if isinstance(path, list) else path
    try:
        frappe.get_attr(p)
        log("  OK import:", p)
    except Exception:
        log("  FAIL import:", p)
        traceback.print_exc()

# now simulate a real desk boot for Administrator
frappe.set_user("Administrator")
try:
    from frappe.desk.desk_page import getpage
    frappe.local.form_dict = {"name": "desktop"}
    getpage("desktop")
    log("desk getpage(desktop) OK")
except Exception:
    log("desk getpage FAILED:")
    traceback.print_exc()
log("DONE 180")
