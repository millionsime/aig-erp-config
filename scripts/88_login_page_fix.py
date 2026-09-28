# 88_login_page_fix.py -- Diagnose + fix the website-router crash ("Not
# Permitted" / 404 on login page). Root cause: redis-cached
# "doctypes_with_web_view" still lists "Job Opening" (HRMS), whose DocType row
# is gone -> frappe.get_meta() raises inside _find_matching_document_webview()
# for every routed path. Fix: frappe.clear_cache() regenerates the list from
# tabDocType. Read-only checks + cache clear only; nothing else is touched.

import frappe


def log(*a):
    print(*a, flush=True)


log("DIAGNOSIS")
log(f"  DocType 'Job Opening' exists: {bool(frappe.db.exists('DocType', 'Job Opening'))}")

rows = frappe.db.sql(
    "select name, module, custom from `tabDocType` where has_web_view = 1 order by name"
)
log(f"  doctypes with has_web_view=1 in DB: {len(rows)}")
for name, module, custom in rows:
    log(f"    - {name} (module={module}, custom={custom})")

missing_in_cache_check = [
    r[0] for r in rows if not frappe.db.exists("DocType", r[0])
]
log(f"  rows listed but not loadable: {missing_in_cache_check or 'none'}")

cached = frappe.cache.get_value("doctypes_with_web_view")
if cached is not None:
    names = [d.get("name") if isinstance(d, dict) else d for d in cached]
    log(f"  CACHED list: {names}")
    stale = [n for n in names if not frappe.db.exists("DocType", n)]
    log(f"  stale entries in cache (cause of the crash): {stale or 'none'}")
else:
    log("  cached list: (empty/absent)")

apps = frappe.get_installed_apps()
log(f"  installed apps: {apps}")

log("")
log("FIX: frappe.clear_cache()")
frappe.clear_cache()
log("  cache cleared")

cached_after = frappe.cache.get_value("doctypes_with_web_view")
names_after = (
    [d.get("name") if isinstance(d, dict) else d for d in cached_after]
    if cached_after is not None
    else "(regenerated lazily on next request)"
)
log(f"  cached list now: {names_after}")

log("")
log("POST-CHECK: simulate the router's web-view lookup")
try:
    from frappe.website.page_renderers.document_page import _find_matching_document_webview

    # bypass the 1h redis memo by clearing it again right before the call
    _find_matching_document_webview("login")
    log("  _find_matching_document_webview('login'): OK (no exception)")
except Exception:
    log(f"  !! still failing: {frappe.get_traceback().strip().splitlines()[-1]}")

log("")
log("DONE -- reload the login page in the browser.")
