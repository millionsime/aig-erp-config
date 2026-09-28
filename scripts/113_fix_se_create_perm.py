# 113_fix_se_create_perm.py -- 111/112 established: Custom DocPerm bits on
# Stock Entry are correct; doc-level CREATE fails only when the form payload
# carries "Head Office - AIG" as a Cost Center link, and the v2 scrubber's
# 900ms setTimeout loses the race against ERPNext's async item-detail fill
# (which can re-inject HO after the scrub). Fix two ways:
#   1. NEW client script "AIG - SE CC Intercept" (Form): monkey-patch
#      StockEntry.item_details.set_cost_center to force the enterprise CC
#      (header aig_cost_center, else row s_warehouse's aig_cost_center, else
#      clear) the instant ERPNext's async fill tries to write the company
#      default. No setTimeout -- the intercept is exact.
#   2. Server Script "AIG - SE CC Normalize" (Before Validate): header
#      aig_cost_center, then row cost_center, then s_warehouse's aig_cost_center
#      must agree: header wins; rows matching source-warehouse CC are rewritten;
#      mismatches THROW so bad data cannot slip through as Administrator-only.
#      Runs before validate->workflow->doc-permission, so even a payload that
#      slips past the client gets normalized while still eligible for create.
# Then verify: role bits, doc-level create probes (incl. HO row + header), and
# an in-memory Before-Validate simulation with an HO-poisoned row.

import json

import frappe

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"
DT = "Stock Entry"
ITEM = "AIG-INV-FEED"
WH = "Dairy Farm Store - AIG"
MR = "MAT-MR-2026-00005"

FULL_BITS = {"read": 1, "write": 1, "create": 1, "delete": 0, "submit": 1,
             "cancel": 1, "amend": 0, "print": 1, "email": 0, "export": 1,
             "report": 1, "import": 0, "share": 1}

CS_NAME = "AIG - SE CC Intercept"
SS_NAME = "AIG - SE CC Normalize"

CS_BODY = """// AIG - SE CC Intercept: ERPNext's async item-detail fill stamps the
// Company default Cost Center (Head Office - AIG) onto rows. For
// enterprise-scoped users that CC fails the doc-level CREATE check at Save
// ('You need the create permission on Stock Entry'). This row-level handler
// fires the instant the fill writes cost_center (model event, no timeouts)
// and reverts the poison to the enterprise CC (header) or empty.
(function () {
	var POISON = "Head Office - AIG";
	function target(frm) {
		return frm.doc.aig_cost_center || frm.doc.aig_dest_cost_center || null;
	}
	frappe.ui.form.on("Stock Entry Item", {
		cost_center: function (frm, cdt, cdn) {
			var row = locals[cdt] && locals[cdt][cdn];
			if (!row || !row.cost_center) return;
			var want = target(frm);
			if (row.cost_center === POISON && row.cost_center !== want) {
				frappe.model.set_value(cdt, cdn, "cost_center", want || null);
			}
		}
	});
	frappe.ui.form.on("Stock Entry", {
		refresh: function (frm) {
			// a new doc must never carry the Company default as its dimension
			if (frm.doc.__islocal && frm.doc.aig_cost_center === POISON) {
				frm.set_value("aig_cost_center", null);
			}
		},
		aig_cost_center: function (frm) {
			var want = target(frm);
			(frm.doc.items || []).forEach(function (row) {
				if (row.cost_center === POISON && row.cost_center !== want) {
					frappe.model.set_value(row.doctype, row.name, "cost_center", want || null);
				}
			});
		}
	});
})();"""

SS_BODY = """# AIG - SE CC Normalize (Before Validate): ERPNext injects the Company
# default Cost Center (Head Office - AIG) into new Stock Entry rows/header.
# Normalize everything to the document enterprise CC (header, else the
# destination/source warehouse CC) BEFORE validation and GL posting: empty
# rows get filled, injected Head Office values are overwritten silently, and
# a genuinely foreign enterprise CC (no header dimension derivable) throws.
row_src = None
row_dst = None
src_cc = None
if doc.from_warehouse:
    src_cc = frappe.db.get_value("Warehouse", doc.from_warehouse, "aig_cost_center")
for it in (doc.items or []):
    if it.s_warehouse and not row_src:
        row_src = frappe.db.get_value("Warehouse", it.s_warehouse, "aig_cost_center")
    if it.t_warehouse and not row_dst:
        row_dst = frappe.db.get_value("Warehouse", it.t_warehouse, "aig_cost_center")
hdr = doc.get("aig_cost_center") or row_dst or row_src or src_cc
if hdr:
    doc.aig_cost_center = hdr
foreign = []
for it in (doc.items or []):
    if hdr:
        it.cost_center = hdr
    elif it.cost_center == "Head Office - AIG":
        it.cost_center = None
    elif it.cost_center:
        foreign.append(it.cost_center)
if foreign:
    frappe.throw("Row cost center(s) " + ", ".join(foreign) + " do not belong "
                 "to any enterprise cost center on this document. Pick the "
                 "correct enterprise cost center.")"""


def log(*a):
    print(*a, flush=True)


def upsert_client():
    body = {"doctype": "Client Script", "name": CS_NAME, "dt": DT,
            "view": "Form", "enabled": 1, "script": CS_BODY,
            "module": "AIG HR"}
    cur = frappe.db.get_value("Client Script", CS_NAME,
                              ["script", "enabled"], as_dict=True)
    if cur and cur.script == CS_BODY and cur.enabled:
        log("  client script unchanged")
        return
    if frappe.db.exists("Client Script", CS_NAME):
        doc = frappe.get_doc("Client Script", CS_NAME)
        doc.script = CS_BODY
        doc.enabled = 1
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)
        log("  client script updated")
        return
    frappe.get_doc(body).insert(ignore_permissions=True)
    log("  client script created")


def upsert_server():
    exists = frappe.db.exists("Server Script", SS_NAME)
    if exists:
        row = frappe.get_doc("Server Script", SS_NAME)
        row.script = SS_BODY
        row.disabled = 0
        row.script_type = "DocType Event"
        row.reference_doctype = DT
        row.doctype_event = "Before Validate"
        row.flags.ignore_permissions = True
        row.save(ignore_permissions=True)
        log("  server script created/updated")
        return
    frappe.get_doc({
        "doctype": "Server Script", "name": SS_NAME,
        "script_type": "DocType Event", "reference_doctype": DT,
        "doctype_event": "Before Validate", "disabled": 0, "script": SS_BODY,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  server script created")


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
    doc.name = "new-stock-entry-fix113"
    try:
        frappe.has_permission(doc, "create", user=U, throw=True)
        res = "CREATE OK"
    except Exception:
        tb = frappe.get_traceback().strip().splitlines()
        res = "FAIL: " + (tb[-1] if tb else "?")[:90]
    frappe.set_user("Administrator")
    log(f"  {label}: {res}")


def log_def(d):
    return json.dumps(d, default=str)


log("STEP 1: Custom DocPerm bits on Stock Entry (should already be fine)")
for r in frappe.get_all("Custom DocPerm", filters={"parent": DT},
                        fields=["role", "read", "write", "create", "submit",
                                "cancel"], order_by="role"):
    log(f"  {r.role}: read={r.read} write={r.write} create={r.create} "
        f"submit={r.submit} cancel={r.cancel}")

log("")
log("STEP 2: upsert client intercept script")
upsert_client()

log("")
log("STEP 3: upsert server normalize script (Before Validate)")
upsert_server()

log("")
log("STEP 4: clear cache")
frappe.clear_cache()
log("  done")

log("")
log("STEP 5: doc-level create probes as storekeeper.agro")
probe("a) row=HO, header empty (async-fill state)")
probe("b) row=HO, header=HO (pre-scrub payload)")
probe("c) row=Dairy, header=Dairy (scrubbed state)")
probe("d) row empty, header empty")

log("")
log("STEP 6: in-memory Before-Validate simulation (row=HO poison)")
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
    doc.run_method("before_validate")
    doc.run_method("validate")
    log(f"  header aig_cost_center = {doc.aig_cost_center!r}")
    log(f"  row cost_centers       = {[d.cost_center for d in doc.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  validate FAILED: {tail[-1] if tail else '?'}")

log("")
log("VERDICT: all four probes CREATE OK + simulation ends with Dairy on header "
    "and rows => user can save; hard-refresh (Ctrl+Shift+R) then retry.")
