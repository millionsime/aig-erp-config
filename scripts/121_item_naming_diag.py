# 121_item_naming_diag.py -- User wants new Item Codes auto-generated as
# "AIG-<4-digit>-<4-digit>" (two incremental 4-digit numbers). Diagnose the
# v16 naming engine (does "AIG-.####.-.####" work? shared or separate
# counters?), current Item.autoname, Stock Settings item_naming_by, the
# naming_series field options, and existing AIG items. READ-ONLY (a counter
# probe would commit; we only inspect source + config).

import inspect

import frappe
from frappe.model import naming


def log(*a):
    print(*a, flush=True)


log("1) naming engine source (make_autoname / parse_naming_series / getseries)")
for fn in ("make_autoname", "parse_naming_series", "getseries"):
    f = getattr(naming, fn, None)
    if f:
        log(f"--- {fn} ---")
        log(inspect.getsource(f))
    else:
        log(f"--- {fn}: NOT FOUND; naming module has: "
            f"{[x for x in dir(naming) if 'ser' in x.lower() or 'auto' in x.lower()]} ---")

log("")
log("2) Item doctype autoname:",
    frappe.get_doc("DocType", "Item").autoname)

st = frappe.get_doc("Stock Settings")
log("3) Stock Settings item_naming_by:", st.get("item_naming_by"))

log("")
log("4) Item naming_series field")
for f in frappe.get_meta("Item").fields:
    if f.fieldname == "naming_series":
        log(f"  options={f.options!r} default={f.default!r} hidden={f.hidden} "
            f"fieldtype={f.fieldtype}")

log("")
log("5) existing AIG items")
for r in frappe.get_all("Item", filters={"name": ["like", "AIG%"]}, pluck="name"):
    log("  ", r)

log("")
log("6) tabSeries rows for AIG")
rows = frappe.db.sql("select name, current from tabSeries where name like 'AIG%'",
                     as_dict=True)
for r in rows:
    log("  ", r)
if not rows:
    log("  (none)")
