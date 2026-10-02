# 181b_bootinfo_probe2.py -- READ-ONLY: v16 bootinfo signature (no args).
import frappe
import traceback

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")
from frappe.boot import get_bootinfo
try:
    bi = get_bootinfo()
    flag = getattr(bi, "aig_ethiopian_calendar", None)
    log("bootinfo OK; flag =", flag)
except Exception:
    log("get_bootinfo() FAILED:")
    traceback.print_exc()

# replicate what boot_session hooks do during a real request
for path in frappe.get_hooks("boot_session") or []:
    try:
        fn = frappe.get_attr(path)
        bi2 = frappe._dict()
        fn(bi2)
        log("hook", path, "-> keys:", [k for k in bi2.keys()][:6])
    except Exception:
        log("hook", path, "FAILED:")
        traceback.print_exc()
log("DONE 181b")
