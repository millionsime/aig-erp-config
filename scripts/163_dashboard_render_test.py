# 163_dashboard_render_test.py -- render the AIG admin dashboard page with
# the real Jinja environment (Administrator) so template/controller errors
# surface here first. Read-only.
import frappe


def log(*a):
    print(*a, flush=True)


frappe.set_user("Administrator")
from frappe.utils.jinja import get_jenv  # noqa: E402

try:
    jenv = get_jenv()
    html = jenv.get_template("www/aig-admin.html").render(
        frappe._dict({"data": None})
    )
    log("UNEXPECTED: rendered without context")
except frappe.Redirect:
    log("OK: Redirect raised (expected only when unauthenticated/guest - "
        "Administrator must NOT redirect)")
except Exception as e:
    log(f"render exception (inspect): {type(e).__name__}: {e}")

# full path: call get_context like the www resolver would
try:
    import importlib
    spec = importlib.util.spec_from_file_location(
        "aig_admin",
        "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/www/aig-admin.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ctx = frappe._dict()
    mod.get_context(ctx)
    log("controller OK")
    log(f"  kpi: {ctx.data['kpi']}")
    log(f"  po_by_state: {ctx.data['po_by_state']}")
    log(f"  pending: {len(ctx.data['pending'])} rows")
    log(f"  trend weeks: {len(ctx.data['po_trend'])} "
        f"nonzero={sum(1 for t in ctx.data['po_trend'] if t['value'])}")
    log(f"  top suppliers: {ctx.data['top_suppliers']}")
    # now render the template with the real context
    from frappe.utils.jinja import get_jenv as _gj
    jenv = _gj()
    html = jenv.get_template("www/aig-admin.html").render(
        {"data": ctx.data, "data_json": ctx.data_json,
         "site_name": ctx.site_name})
    log(f"template render OK: {len(html)} chars")
    for needle in ["AIG_DATA", "po-donut", "Needs Attention",
                   "aig-dash", "MR by state"]:
        log(f"  contains {needle!r}: {needle in html}")
except Exception:
    import traceback
    log("!! controller/render FAILED:")
    log(traceback.format_exc())
log("DONE 163")
