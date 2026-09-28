# 164_dashboard_verify.py -- end-to-end verification of /aig-admin:
#   A) full template render (my blocks) against a stub base with the REAL
#      controller context - catches every runtime error in my markup
#   B) live HTTP: /aig-admin as Guest must 302 to /login (guard + routing)
# Read-only.
import frappe


def log(*a):
    print(*a, flush=True)


frappe.set_user("Administrator")

# --- A) render with a stub base -------------------------------------------
import importlib.util  # noqa: E402
from jinja2 import Environment, DictLoader  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "aig_admin",
    "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/www/aig-admin.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ctx = frappe._dict()
mod.get_context(ctx)

src = open("/home/frappe/frappe-bench/apps/custom_theme/custom_theme/"
           "www/aig-admin.html").read()
STUB = ("{% block title %}{% endblock %}"
        "{% block page_content %}{% endblock %}")
env = Environment(loader=DictLoader({
    "aig-admin.html": src,
    "templates/web.html": STUB,
}))
html = env.get_template("aig-admin.html").render({
    "data": ctx.data, "data_json": ctx.data_json,
    "site_name": ctx.site_name,
})
log(f"A) template render OK: {len(html)} chars")
checks = ["AIG_DATA", "po-donut", "po-legend", "mr-bars", "po-pipe",
          "Needs Attention", "Committed Spend Trend", "Top Suppliers",
          "492,825", "Blue Nile Trade PLC", "Pending Committee Signoff",
          "aig-clock", "Refresh"]
bad = [c for c in checks if c not in html]
log(f"   all {len(checks)} content checks passed: {not bad}"
    + (f" MISSING: {bad}" if bad else ""))

# --- B) live HTTP ----------------------------------------------------------
import requests  # noqa: E402

BASE = "http://localhost:8080"
r0 = requests.get(BASE + "/", timeout=15)
log(f"B) site up: GET / -> {r0.status_code} "
    f"({r0.headers.get('content-type', '')[:30]})")
r1 = requests.get(BASE + "/aig-admin", timeout=15,
                  allow_redirects=False)
loc = r1.headers.get("Location", "")
log(f"   GET /aig-admin (Guest) -> {r1.status_code} Location={loc!r}")
guard_ok = (r1.status_code in (301, 302)
            and "/login" in loc and "aig-admin" in loc)
log(f"   guard + routing OK: {guard_ok}")
if not (r0.status_code == 200 and guard_ok and not bad):
    raise SystemExit("dashboard verification FAILED")
log("DONE 164 - open http://<host>:8080/aig-admin as Administrator")
