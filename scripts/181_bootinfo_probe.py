# 181_bootinfo_probe.py -- READ-ONLY: run get_bootinfo as Administrator to
# surface the exact exception behind the desk 500, and confirm the flag.
import frappe
import traceback

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")
from frappe.boot import get_bootinfo
bi = frappe._dict()
try:
    get_bootinfo(bi)
    log("bootinfo OK; flag =", getattr(bi, "aig_ethiopian_calendar", "MISSING"))
    log("sysdefaults keys sample:", list((bi.sysdefaults or {}).keys())[:5])
except Exception:
    log("get_bootinfo FAILED:")
    traceback.print_exc()

# also try the workspace the /app route renders
try:
    from frappe.desk.desktop import get_desk_sidebar_items
    get_desk_sidebar_items()
    log("sidebar OK")
except Exception:
    log("sidebar FAILED:")
    traceback.print_exc()
log("DONE 181")
