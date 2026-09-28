# AIG config - step 44: INVENTORY role workspaces + navigation (config layer).
# Creates role-gated Workspaces that surface the main inventory tasks and reuse the
# BUILT-IN permission-respecting stock reports (no duplicate report code, no core
# edits). Schema mirrors the stock "Stock" workspace: content = JSON card blocks,
# links = "Card Break" + "Link" child rows.
import frappe
import json
import traceback

MODULE = "Stock"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def _id(n):
    return f"aigws{n:04d}"


def build_workspace(label, roles, cards, for_user=None):
    """cards = [ (card_label, [ (link_label, link_type, is_query_report, report_ref_doctype), ... ]), ... ]"""
    # links child rows
    links = []
    content = []
    n = 0
    for card_label, entries in cards:
        links.append({"type": "Card Break", "label": card_label})
        n += 1
        content.append({"id": _id(n), "type": "card",
                        "data": {"card_name": card_label, "col": 4}})
        for (ll, ltype, iqr, rrd) in entries:
            row = {"type": "Link", "label": ll, "link_type": ltype}
            if iqr:
                row["is_query_report"] = 1
            if rrd:
                row["report_ref_doctype"] = rrd
            links.append(row)

    existing = frappe.db.get_value("Workspace", {"label": label}, "name")
    if existing:
        ws = frappe.get_doc("Workspace", existing)
        ws.set("links", [])
        for l in links:
            ws.append("links", l)
        ws.content = json.dumps(content)
        ws.module = MODULE
        ws.public = 0
        ws.for_user = for_user or ""
        ws.set("roles", [])
        for r in roles:
            ws.append("roles", {"role": r})
        ws.flags.ignore_permissions = True
        try:
            ws.save(ignore_permissions=True)
            log("UPDATE", f"Workspace {label} ({len(links)} links, roles={roles})")
        except Exception:
            print(f"!! FAILED update {label}")
            print(traceback.format_exc())
        return label

    ws = frappe.get_doc({
        "doctype": "Workspace", "label": label, "title": label, "module": MODULE,
        "public": 0, "for_user": for_user or "", "is_hidden": 0,
        "content": json.dumps(content), "parent_page": "",
        "links": links,
        "roles": [{"role": r} for r in roles],
    })
    ws.flags.ignore_permissions = True
    try:
        ws.insert(ignore_permissions=True)
        log("CREATE", f"Workspace {label} ({len(links)} links, roles={roles})")
    except Exception:
        print(f"!! FAILED create {label}")
        print(traceback.format_exc())
    return label


INV_ADMIN = "AIG Inventory Administrator"
MAIN_STORE_ADMIN = "AIG Main Store Administrator"
GEN_STORE_KEEPER = "AIG General Store Keeper"
STORE_KEEPER = "AIG Store Keeper"
PROP_EXPERT = "AIG Property Admin Expert"
END_USER = "AIG End User"
AUDITOR = "AIG Internal Auditor"
ENT_HEAD = "AIG Enterprise Head"
FINANCE = "AIG Finance"

# 1) Requests & approvals - requester + approvers
build_workspace(
    "AIG Inventory Requests",
    [END_USER, MAIN_STORE_ADMIN, ENT_HEAD, INV_ADMIN, AUDITOR],
    [
        ("Stock Requests (Model 19)", [
            ("Material Request", "DocType", 0, None),
            ("Item", "DocType", 0, None),
        ]),
        ("Approvals", [
            ("Material Request", "DocType", 0, None),
            ("Quality Inspection", "DocType", 0, None),
        ]),
        ("My Enterprise", [
            ("Warehouse", "DocType", 0, None),
            ("Cost Center", "DocType", 0, None),
        ]),
    ],
)

# 2) Store operations - receiving, issue, transfer, counts
build_workspace(
    "AIG Store Operations",
    [STORE_KEEPER, GEN_STORE_KEEPER, MAIN_STORE_ADMIN, INV_ADMIN],
    [
        ("Receive / Issue / Transfer", [
            ("Stock Entry", "DocType", 0, None),
            ("Quality Inspection", "DocType", 0, None),
            ("Material Request", "DocType", 0, None),
        ]),
        ("Counts & Adjustments", [
            ("Stock Reconciliation", "DocType", 0, None),
            ("Stock Ledger", "Report", 1, None),
        ]),
        ("Masters", [
            ("Item", "DocType", 0, None),
            ("Warehouse", "DocType", 0, None),
            ("Item Group", "DocType", 0, None),
        ]),
    ],
)

# 3) Property administration - bins / barcodes / asset tags
build_workspace(
    "AIG Property Administration",
    [PROP_EXPERT, INV_ADMIN],
    [
        ("Bins / Barcodes / Tags", [
            ("Item", "DocType", 0, None),
            ("Stock Entry", "DocType", 0, None),
        ]),
        ("Receiving to Assign", [
            ("Stock Entry", "DocType", 0, None),
            ("Quality Inspection", "DocType", 0, None),
        ]),
    ],
)

# 4) Reports & audit - auditor / finance / admin / enterprise head
build_workspace(
    "AIG Inventory Reports & Audit",
    [AUDITOR, FINANCE, INV_ADMIN, ENT_HEAD, MAIN_STORE_ADMIN],
    [
        ("Stock Reports", [
            ("Stock Ledger", "Report", 1, None),
            ("Stock Balance", "Report", 1, None),
            ("Stock Projected Qty", "Report", 1, None),
            ("Stock Ageing", "Report", 1, None),
        ]),
        ("Requests & Movements", [
            ("Material Request", "DocType", 0, None),
            ("Stock Entry", "DocType", 0, None),
            ("Stock Reconciliation", "DocType", 0, None),
        ]),
        ("Valuation", [
            ("Stock Analytics", "Report", 1, None),
            ("Item Price Stock", "Report", 1, None),
            ("Warehouse Wise Stock Balance", "Report", 0, "Stock Ledger Entry"),
        ]),
    ],
)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP44_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
