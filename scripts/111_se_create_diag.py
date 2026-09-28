# 111_se_create_diag.py -- Diagnose "You need the 'create' permission on Stock
# Entry" when storekeeper.agro clicks Save on the issue Stock Entry form.
# (a) Dump Custom DocPerm BITS on Stock Entry for every role.
# (b) Doc-level create probes as storekeeper.agro in several CC states
#     (empty / HO / Dairy) to see whether the failure is role-bit or scope.
# (c) Fix: if a Custom DocPerm row exists but lacks bits, OR a store role has
#     no row at all, write full workflow-controlled rows (read/write/create/
#     submit/cancel/amend -- workflow controls actual posting state).
# (d) Clear cache and re-run probes.
# One pass: dump bits -> doc-level probes -> fix -> clear cache -> re-verify.
# Idempotent; runner commits only on success.
# Run via run_script.sh. Runs diag + fix + verify in one pass (idempotent);
# fix is commit-on-success safe.

import frappe

COMPANY = "Adama Investment Group"
U = "storekeeper.agro@aig.local"
DT = "Stock Entry"
APPROVED_MR = None  # auto-detect an Approved Material Request

STORE_ROLES = ["AIG Store Keeper", "AIG Main Store Administrator",
               "AIG General Store Keeper", "AIG Inventory Administrator"]

FULL_BITS = {"read": 1, "write": 1, "create": 1, "delete": 0, "submit": 1,
             "cancel": 1, "amend": 1, "print": 1, "email": 0, "export": 1,
             "report": 1, "import": 0, "share": 1, "set_user_permissions": 0}

READONLY_BITS = {"read": 1, "write": 0, "create": 0, "delete": 0, "submit": 0,
                 "cancel": 0, "amend": 0, "print": 0, "email": 0, "export": 0,
                 "report": 0, "import": 0, "share": 0, "set_user_permissions": 0}


def log(*a):
    print(*a, flush=True)


def find_approved_mr():
    mrs = frappe.get_all("Material Request",
                         filters={"docstatus": 1,
                                  "workflow_state": ["like", "%Approved%"]},
                         order_by="modified desc", limit=1, pluck="name")
    return mrs[0] if mrs else None


def dump_bits():
    log("1) CUSTOM DOCPERM BITS on Stock Entry (v16: parent=doctype)")
    rows = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": DT},
        fields=["name", "role", "permlevel", "read", "write", "create",
                "submit", "cancel", "amend"],
        order_by="role, permlevel",
    )
    for r in rows:
        log(f"  {r.role} L{r.permlevel}: read={r.read} write={r.write} "
            f"create={r.create} submit={r.submit} cancel={r.cancel} amend={r.amend}")
    if not rows:
        log("  (no Custom DocPerm rows -- standard DocPerms apply)")
    log("")
    log("2) STANDARD DOCPERM roles (shadowed when custom rows exist)")
    std = frappe.get_all("DocPerm", filters={"parent": DT},
                         fields=["role", "create", "write", "submit", "cancel"])
    for r in std:
        log(f"  {r.role}: create={r.create} write={r.write} submit={r.submit} cancel={r.cancel}")
    log("")
    log("3) ROLE MEMBERSHIP for the storekeeper user")
    log(f"  {U}: {frappe.get_all('Has Role', filters={'parent': U, 'parenttype': 'User'}, pluck='role')}")


def probe(label, purpose="Material Issue", cost_center=None, aig_cc=None,
          warehouse="Dairy Farm Store - AIG"):
    frappe.set_user(U)
    doc = frappe.new_doc(DT)
    doc.company = COMPANY
    doc.stock_entry_type = "Material Issue"
    doc.purpose = purpose
    doc.from_warehouse = warehouse
    doc.aig_material_request = APPROVED_MR
    doc.append("items", {
        "item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
        "s_warehouse": warehouse,
        **({"cost_center": cost_center} if cost_center else {}),
    })
    if aig_cc:
        doc.aig_cost_center = aig_cc
    doc.name = "new-stock-entry-diag111"  # mimic the client temp name
    try:
        frappe.has_permission(doc, "create", user=U, throw=True)
        res = "CREATE OK"
    except Exception:
        tb = frappe.get_traceback().strip().splitlines()
        res = "CREATE FAIL: " + (tb[-1] if tb else "?")[:120]
    frappe.set_user("Administrator")
    log(f"  {label}: {res}")


def probes():
    log("4) DOC-LEVEL CREATE PROBES as storekeeper.agro")
    probe("A: empty CC (scrubbed form)")
    probe("B: HO CC (injected before scrub)", cost_center="Head Office - AIG",
          aig_cc="Head Office - AIG")
    probe("C: Dairy CC", cost_center="Dairy Farm - AIG", aig_cc="Dairy Farm - AIG")
    log("")


def set_bits(role, bits):
    existing = frappe.db.get_value("Custom DocPerm", {"parent": DT, "role": role}, "name")
    if existing:
        cur = frappe.db.get_value("Custom DocPerm", existing,
                                  ["read", "write", "create", "submit", "cancel", "amend"],
                                  as_dict=True)
        if all(getattr(cur, k) == v for k, v in bits.items()):
            log(f"  ok (no change): {role}")
            return
        for k, v in bits.items():
            frappe.db.set_value("Custom DocPerm", existing, k, v, update_modified=False)
        log(f"  updated bits: {role}")
        return
    frappe.get_doc({"doctype": "Custom DocPerm", "parent": DT,
                    "parenttype": "DocType", "parentfield": "permissions",
                    "role": role, **bits}).insert(ignore_permissions=True)
    log(f"  created row: {role}")


def fix():
    log("5) FIX: ensure full rows on Stock Entry")
    log("  -- store roles get full workflow-controlled bits --")
    for role in STORE_ROLES:
        set_bits(role, FULL_BITS)
    log("  -- every other custom row keeps at least read --")
    for r in frappe.get_all("Custom DocPerm", filters={"parent": DT},
                            fields=["name", "role"]):
        if not frappe.db.get_value("Custom DocPerm", r.name, "read"):
            frappe.db.set_value("Custom DocPerm", r.name, "read", 1, update_modified=False)
            log(f"  read=1 -> {r.role}")
    log("")
    log("6) clear cache")
    frappe.clear_cache()
    log("  done")
    log("")
    log("7) RE-VERIFY role-level + doc-level create")
    for role in STORE_ROLES:
        row = frappe.db.get_value("Custom DocPerm", {"parent": DT, "role": role}, "name")
        if row:
            b = frappe.db.get_value("Custom DocPerm", row,
                                    ["read", "write", "create", "submit", "cancel"], as_dict=True)
            log(f"  {role}: read={b.read} write={b.write} create={b.create} "
                f"submit={b.submit} cancel={b.cancel}")
    ok = frappe.has_permission(DT, "create", user=U, throw=False)
    log(f"  role-level create {U}: {bool(ok)}")
    probe("RE-VERIFY A: empty CC")
    probe("RE-VERIFY B: HO CC", cost_center="Head Office - AIG", aig_cc="Head Office - AIG")
    probe("RE-VERIFY C: Dairy CC", cost_center="Dairy Farm - AIG", aig_cc="Dairy Farm - AIG")


APPROVED_MR = find_approved_mr()
log(f"approved MR for probes: {APPROVED_MR}")

dump_bits()
probes()
# NOTE: bits were verified fine on the first run; the real cause was the Head
# Office CC injected into the form payload (see 112). Fix scripts live in 113.
