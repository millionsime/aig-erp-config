# 179_global_defaults.py -- FIX (commits on success): desk dashboard charts
# ("Sales Order Trends", "Top Customers", ...) show "Company is mandatory"
# when Global Defaults has no default company. Set it (+ default currency)
# and clear cache. Re-run this on the deployment server after company creation.
import frappe

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")

gd = frappe.get_doc("Global Defaults", "Global Defaults")
log("before:", "company =", gd.default_company, "| currency =", gd.default_currency)

changed = False
if not gd.default_company:
    gd.default_company = "Adama Investment Group"
    changed = True
if not gd.default_currency:
    gd.default_currency = "ETB"
    changed = True

if changed:
    gd.save(ignore_permissions=True)
    frappe.clear_cache()
    log("saved + cache cleared")
else:
    log("already set - nothing to do")

gd.reload()
log("after: ", "company =", gd.default_company, "| currency =", gd.default_currency)

# sanity: the Selling dashboard charts should now resolve a company
company = frappe.defaults.get_global_default("company")
log("global default 'company' resolves to:", company)
if company != "Adama Investment Group":
    raise Exception("global default company not set as expected")
log("DONE 179")
