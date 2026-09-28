# 115_fix_stock_adjustment_account.py -- 114's real insert() test exposed a
# config gap that would also break the Saturday demo: Company has no default
# "Stock Adjustment (Difference) Account" (used by Stock Entry rounding and
# Stock Reconciliation valuation differences). ERPNext v16 expects an
# Expense-type account. Wire it, clear cache, and re-verify the save path:
#   TEST 1: storekeeper.agro insert() clean issue SE (the exact browser payload
#           after the new intercept) -- must succeed.
#   TEST 2: Administrator insert() with an HO-poisoned row CC -- "AIG - SE CC
#           Normalize" must rewrite it to the enterprise CC (safety net).
# Both test docs are deleted afterwards; idempotent (runner commits on success).

import frappe

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"
DT = "Stock Entry"
WH = "Dairy Farm Store - AIG"
MR = "MAT-MR-2026-00005"

CREATED = []


def log(*a):
    print(*a, flush=True)


# ---- STEP 1: find-or-create the expense account --------------------------
log("STEP 1: default Stock Adjustment Account")
candidates = frappe.get_all("Account",
                            filters={"company": COMPANY,
                                     "account_type": "Stock Adjustment",
                                     "is_group": 0},
                            pluck="name")
acct = candidates[0] if candidates else None
if acct:
    log(f"  found existing: {acct}")
else:
    log("  none found -- creating 'Stock Adjustment - AIG' under 5000 roots")
    parent = None
    for p in frappe.get_all("Account", filters={"company": COMPANY,
                                                "account_number": "5019",
                                                "is_group": 1},
                            pluck="name"):
        parent = p
        break
    if not parent:
        for p in frappe.get_all("Account", filters={"company": COMPANY,
                                                    "name": ["like", "5019%"],
                                                    "is_group": 1},
                                pluck="name"):
            parent = p
            break
    if not parent:
        # fall back to any non-root expense group named like operating costs
        for p in frappe.get_all("Account", filters={"company": COMPANY,
                                                    "root_type": "Expense",
                                                    "is_group": 1},
                                fields=["name"], order_by="lft", limit=20):
            if p.name.startswith(("50", "Operating")):
                parent = p.name
                break
    if not parent:
        for p in frappe.get_all("Account", filters={"company": COMPANY,
                                                    "root_type": "Expense",
                                                    "is_group": 1},
                                fields=["name"], order_by="lft"):
            parent = p.name
            break
    log(f"  parent group: {parent}")
    acct = frappe.db.exists("Account", {"account_name": "Stock Adjustment",
                                        "company": COMPANY})
    if not acct:
        doc = frappe.get_doc({
            "doctype": "Account",
            "account_name": "Stock Adjustment",
            "account_number": "5099",
            "parent_account": parent,
            "company": COMPANY,
            "account_type": "Stock Adjustment",
            "account_currency": "ETB",
            "report_type": "Profit and Loss",
            "root_type": "Expense",
        })
        doc.flags.ignore_permissions = True
        doc.insert(ignore_permissions=True)
        acct = doc.name
        CREATED.append(("Account", acct))
    log(f"  account ready: {acct}")

# ---- STEP 2: wire it as the company default ------------------------------
comp = frappe.get_doc("Company", COMPANY)
if comp.stock_adjustment_account == acct:
    log("STEP 2: company default already set")
else:
    comp.db_set("stock_adjustment_account", acct, update_modified=False)
    log(f"STEP 2: company default set -> {acct}")
frappe.clear_cache()
log("  cache cleared")

# ---- STEP 3: save-path verification --------------------------------------
def mr_item():
    row = frappe.get_all("Material Request Item",
                         filters={"parent": MR}, fields=["item_code", "qty"],
                         limit=1)
    return (row[0].item_code, row[0].qty) if row else ("AIG-INV-FEED", 1)


ITEM_CODE, MR_QTY = mr_item()


def build(as_user, row_cc):
    frappe.set_user(as_user)
    doc = frappe.new_doc(DT)
    doc.company = COMPANY
    doc.stock_entry_type = "Material Issue"
    doc.purpose = "Material Issue"
    doc.from_warehouse = WH
    doc.aig_material_request = MR
    item = {"item_code": ITEM_CODE, "qty": 1, "basic_rate": 40,
            "s_warehouse": WH}
    if row_cc:
        item["cost_center"] = row_cc
    doc.append("items", item)
    return doc


def cleanup(docname):
    frappe.set_user("Administrator")
    if docname and frappe.db.exists(DT, docname):
        frappe.delete_doc(DT, docname, ignore_permissions=True, force=True)
        log(f"  cleaned up test doc {docname}")


log("")
log(f"TEST 1: real insert() as {U} with CLEAN payload (item {ITEM_CODE} from MR)")
name1 = None
try:
    doc = build(U, None)
    doc.insert(ignore_permissions=False)
    name1 = doc.name
    log(f"  INSERT OK: {name1}")
    log(f"    workflow_state    = {doc.workflow_state}")
    log(f"    header aig_cost_center = {doc.aig_cost_center!r}")
    log(f"    row cost_centers  = {[d.cost_center for d in doc.items]}")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")
finally:
    cleanup(name1)

log("")
log("TEST 2: real insert() as Administrator with HEAD-OFFICE-poisoned row")
name2 = None
try:
    doc = build("Administrator", "Head Office - AIG")
    doc.insert(ignore_permissions=True)
    name2 = doc.name
    log(f"  INSERT OK: {name2}")
    log(f"    header aig_cost_center = {doc.aig_cost_center!r} (expect Dairy)")
    log(f"    row cost_centers  = {[d.cost_center for d in doc.items]} (expect Dairy)")
except Exception:
    tail = frappe.get_traceback().strip().splitlines()
    log(f"  INSERT FAILED: {tail[-1] if tail else '?'}")
finally:
    cleanup(name2)

log("")
log("VERDICT: TEST 1 OK => the browser Save will now work (Ctrl+Shift+R first).")
