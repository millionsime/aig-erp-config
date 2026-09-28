# 112_se_ho_injector.py -- 111 proved: Custom DocPerm bits on Stock Entry are
# fine; doc-level CREATE fails only when the payload carries Head Office - AIG
# as a Cost Center link. This script finds WHO injects HO and WHICH field trips
# the check. READ-ONLY (no DB writes): dumps client/server scripts, item
# defaults, get_item_details output (what the form async-fills), a probe matrix
# (row CC vs header aig_cost_center), storekeeper user-permission rows, and an
# in-memory validate simulation as Administrator.

import frappe

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"
ITEM = "AIG-INV-FEED"
DT = "Stock Entry"
WH = "Dairy Farm Store - AIG"
MR = "MAT-MR-2026-00005"


def log(*a):
    print(*a, flush=True)


log("1) CLIENT SCRIPTS in the 'Row CC Scrub' family")
for r in frappe.get_all("Client Script",
                        filters={"name": ["like", "%Row CC Scrub%"]},
                        fields=["name", "dt", "view", "enabled"],
                        order_by="name"):
    log(f"  --- {r.name} (dt={r.dt} view={r.view} event={r.event} enabled={r.enabled}) ---")
    log(frappe.db.get_value("Client Script", r.name, "script"))

log("")
log("2) SERVER SCRIPTS on Stock Entry")
for name in ["AIG - SE Movement Defaults", "AIG - SE Item Cost Center Sync"]:
    meta = frappe.db.get_value("Server Script", name,
                               ["script_type", "disabled"], as_dict=True)
    log(f"  --- {name} ({meta}) ---")
    log("  " + (frappe.db.get_value("Server Script", name, "script") or "(missing)")
        .replace("\n", "\n  ")[:1500])

log("")
log("3) ITEM DEFAULTS for AIG-INV-FEED")
for r in frappe.get_all("Item Default", filters={"parent": ITEM}, fields=["*"]):
    keep = {k: r.get(k) for k in ("company", "cost_center", "buying_cost_center",
                                  "selling_cost_center", "expense_account",
                                  "income_account", "default_warehouse")
            if k in r}
    log(f"  {keep}")

log("")
log("4) get_item_details (what the form async-fills after picking an item)")
from erpnext.stock.get_item_details import get_item_details  # noqa
argsets = [
    {"item_code": ITEM, "company": COMPANY, "doctype": DT, "purpose": "Material Issue"},
    {"item_code": ITEM, "company": COMPANY, "doctype": DT, "purpose": "Material Issue",
     "s_warehouse": WH},
]
for args in argsets:
    try:
        out = get_item_details(frappe._dict(args))
        log(f"  args={args.company and dict(args)}")
        log(f"    -> cost_center={out.get('cost_center')} "
            f"expense_account={out.get('expense_account')} uom={out.get('uom')}")
    except Exception:
        tail = frappe.get_traceback().strip().splitlines()
        log(f"  args={dict(args)} -> get_item_details FAILED: {tail[-1] if tail else '?'}")

log("")
log("5) PROBE MATRIX: which Cost Center field trips doc-level CREATE?")


def probe(label, row_cc=None, header_cc=None):
    frappe.set_user(U)
    doc = frappe.new_doc(DT)
    doc.company = COMPANY
    doc.stock_entry_type = "Material Issue"
    doc.purpose = "Material Issue"
    doc.from_warehouse = WH
    doc.aig_material_request = MR
    item = {"item_code": ITEM, "qty": 1, "basic_rate": 40, "s_warehouse": WH}
    if row_cc:
        item["cost_center"] = row_cc
    doc.append("items", item)
    if header_cc:
        doc.aig_cost_center = header_cc
    doc.name = "new-stock-entry-matrix"
    try:
        frappe.has_permission(doc, "create", user=U, throw=True)
        res = "CREATE OK"
    except Exception:
        tb = frappe.get_traceback().strip().splitlines()
        res = "FAIL: " + (tb[-1] if tb else "?")[:90]
    frappe.set_user("Administrator")
    log(f"  {label}: {res}")


probe("a) row=HO,        header=(empty)")
probe("b) row=(empty),   header=HO")
probe("c) row=HO,        header=Dairy")
probe("d) row=Dairy,     header=HO")
probe("e) row=HO,        header=HO     (111 probe B control)")

log("")
log("6) USER PERMISSION rows for storekeeper.agro")
for r in frappe.get_all("User Permission", filters={"user": U},
                        fields=["allow", "for_value", "applicable_for",
                                "apply_to_all_doctypes"],
                        order_by="allow, for_value"):
    log(f"  {r}")

log("")
log("7) IN-MEMORY VALIDATE SIM as Administrator (row=HO, header empty)")
frappe.set_user("Administrator")
doc = frappe.new_doc(DT)
doc.company = COMPANY
doc.stock_entry_type = "Material Issue"
doc.purpose = "Material Issue"
doc.from_warehouse = WH
doc.aig_material_request = MR
doc.append("items", {"item_code": ITEM, "qty": 1, "basic_rate": 40,
                     "s_warehouse": WH, "cost_center": "Head Office - AIG"})
try:
    doc.run_method("validate")
    log(f"  header aig_cost_center = {doc.aig_cost_center!r}")
    log(f"  row cost_centers       = {[d.cost_center for d in doc.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  validate FAILED (in-memory only, nothing saved): {tail[-1] if tail else '?'}")
frappe.set_user("Administrator")
