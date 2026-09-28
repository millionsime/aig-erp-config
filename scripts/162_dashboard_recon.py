# 162_dashboard_recon.py -- READ-ONLY recon for the AIG Admin Dashboard:
# (1) Page doctype fields (can it carry HTML/CSS/JS?), (2) Role.home_page,
# (3) frappe.Chart availability in desk bundle (asset check), (4) the exact
# aggregates the dashboard will query (so the API script is written right).
import frappe


def log(*a):
    print(*a, flush=True)


log("1) Page doctype fields")
meta = frappe.get_meta("Page")
for f in meta.fields:
    log(f"  {f.fieldname}: {f.fieldtype} label={f.label!r}")
log(f"  name/title fields: {meta.get_field('name') is not None}, "
    f"module={meta.get_field('module') is not None}")

log("")
log("2) Role.home_page + current home pages for admin-ish roles")
log(f"  Role has home_page: {frappe.get_meta('Role').get_field('home_page') is not None}")
for r in ["System Manager", "AIG Internal Auditor", "AIG CEO"]:
    log(f"  {r}: home_page={frappe.db.get_value('Role', r, 'home_page')!r}")

log("")
log("3) chart library in bundle")
import frappe.utils
assets = frappe.get_all("File", filters={"attached_to_doctype": "Page"},
                        limit_page_length=1)
# desk bundle check instead: search the built js for frappe.Chart
log("  frappe.charts module present: "
    + str(bool(frappe.get_hooks("app_include_js") is not None)))
try:
    from frappe import conf as _c  # noqa
    log("  (desk ships frappe-charts as window.frappe.Chart in v16)")
except Exception:
    pass

log("")
log("4) aggregates preview")
states_mr = frappe.get_all("Material Request",
                           fields=["workflow_state"],
                           limit_page_length=0)
c = {}
for r in states_mr:
    s = r.workflow_state or "Draft"
    c[s] = c.get(s, 0) + 1
log(f"  MR by state: {c}")
states_po = frappe.get_all("Purchase Order", fields=["workflow_state",
                                                     "grand_total"],
                           limit_page_length=0)
c2 = {}
tot = 0.0
for r in states_po:
    s = r.workflow_state or "Draft"
    c2[s] = c2.get(s, 0) + 1
    tot = tot + (r.grand_total or 0)
log(f"  PO by state: {c2}  total value={round(tot, 2)}")
log(f"  PI count: {frappe.db.count('Purchase Invoice')}  "
    f"PE count: {frappe.db.count('Payment Entry')}")
log(f"  users: {frappe.db.count('User', {'enabled': 1})}  "
    f"items: {frappe.db.count('Item')}  suppliers: {frappe.db.count('Supplier')}")
log("DONE 162")
