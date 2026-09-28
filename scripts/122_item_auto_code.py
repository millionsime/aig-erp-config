# 122_item_auto_code.py -- Automatic Item Codes "AIG-<gggg>-<nnnn>":
#   gggg = stable number of the item's TOP-LEVEL group (stored on the group as
#          aig_group_number; assigned max+1 on first use),
#   nnnn = running counter per group kept in tabSeries under key
#          "AIG-ITEM-<gggg>-" (same mechanism naming series uses).
# Generation happens in a Server Script "AIG - Item Auto Code" (Before Insert)
# so EVERY path is covered (full form, quick entry, API). Users who type a
# code (Administrator) keep it -- generation only fires when item_code is
# empty. Client script makes item_code read-only with a hint for demo users.
# Tests create/insert items, verify codes, then delete the test items and
# reset the touched counters/group numbers so the live demo starts at 0001.

import inspect

import frappe


def log(*a):
    print(*a, flush=True)


log("0) Document.insert order (before_insert vs set_new_name)")
src = inspect.getsource(frappe.model.document.Document.insert)
for i, line in enumerate(src.splitlines()):
    if any(k in line for k in ("before_insert", "set_new_name", "run_before_save",
                               "check_permission")):
        log(f"  L{i}: {line.strip()}")

SS_NAME = "AIG - Item Auto Code"
CS_NAME = "AIG - Item Code Auto Hint"

SS_BODY = """# AIG - Item Auto Code (Before Insert): generate "AIG-<gggg>-<nnnn>" when the
# user left the Item Code empty. gggg = stable number of the top-level Item
# Group (aig_group_number), nnnn = per-group counter (aig_group_seq) kept on
# the Item Group itself -- tabSeries lacks 'creation' and breaks v16 get_value.
# An explicitly typed Item Code (Administrator) is respected untouched.
if not doc.get("item_code"):
    grp = doc.get("item_group")
    if not grp:
        frappe.throw("Select an Item Group first -- AIG generates the Item Code from it.")
    cur = grp
    parent = frappe.db.get_value("Item Group", cur, "parent_item_group")
    depth = 0
    while parent and parent != "All Item Groups" and depth < 10:
        cur = parent
        parent = frappe.db.get_value("Item Group", cur, "parent_item_group")
        depth = depth + 1
    gnum = frappe.db.get_value("Item Group", cur, "aig_group_number")
    if not gnum:
        rows = frappe.get_all("Item Group",
                              filters=[["aig_group_number", ">", 0]],
                              pluck="aig_group_number", order_by="name")
        mx = 0
        for v in rows:
            if int(v or 0) > mx:
                mx = int(v or 0)
        gnum = mx + 1
        frappe.db.set_value("Item Group", cur, "aig_group_number", gnum,
                            update_modified=False)
    gpad = "%04d" % int(gnum)
    seq = frappe.db.get_value("Item Group", cur, "aig_group_seq")
    nxt = int(seq or 0) + 1
    frappe.db.set_value("Item Group", cur, "aig_group_seq", nxt,
                        update_modified=False)
    doc.item_code = "AIG-" + gpad + "-" + ("%04d" % nxt)
"""

CS_BODY = """// AIG - Item Code Auto Hint: demo users never type Item Codes -- the server
// generates AIG-<group>-<sequence> on save. Make the field read-only with a
// hint (Administrator keeps manual override).
(function () {
\tfrappe.ui.form.on("Item", {
\t\trefresh: function (frm) {
\t\t\tif (frappe.session.user === "Administrator") return;
\t\t\tvar df = frm.fields_dict.item_code;
\t\t\tif (df) {
\t\t\t\tdf.df.read_only = 1;
\t\t\t\tdf.df.description = "Leave empty -- AIG generates the code from the Item Group (AIG-<group>-<sequence>).";
\t\t\t\tfrm.refresh_field("item_code");
\t\t\t}
\t\t}
\t});
})();"""


def log(*a):  # noqa: F811
    print(*a, flush=True)


log("")
log("1) custom fields aig_group_number + aig_group_seq on Item Group")
for fname in ("aig_group_number", "aig_group_seq"):
    if frappe.db.exists("Custom Field", "Item Group-" + fname):
        log(f"  exists: {fname}")
    else:
        frappe.get_doc({
            "doctype": "Custom Field", "dt": "Item Group",
            "fieldname": fname, "fieldtype": "Int",
            "label": "AIG Group Number" if fname.endswith("number")
                    else "AIG Group Sequence",
            "insert_after": "parent_item_group" if fname.endswith("number")
                            else "aig_group_number",
            "read_only": 1, "no_copy": 1,
        }).insert(ignore_permissions=True)
        log(f"  created: {fname}")

log("")
log("2) server script (Before Insert)")
if frappe.db.exists("Server Script", SS_NAME):
    row = frappe.get_doc("Server Script", SS_NAME)
    row.script = SS_BODY
    row.disabled = 0
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Server Script", "name": SS_NAME,
        "script_type": "DocType Event", "reference_doctype": "Item",
        "doctype_event": "Before Insert", "disabled": 0, "script": SS_BODY,
        "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  created")

log("")
log("3) client script (readonly hint for demo users)")
if frappe.db.exists("Client Script", CS_NAME):
    row = frappe.get_doc("Client Script", CS_NAME)
    row.script = CS_BODY
    row.enabled = 1
    row.flags.ignore_permissions = True
    row.save(ignore_permissions=True)
    log("  updated")
else:
    frappe.get_doc({
        "doctype": "Client Script", "name": CS_NAME, "dt": "Item",
        "view": "Form", "enabled": 1, "script": CS_BODY, "module": "AIG HR",
    }).insert(ignore_permissions=True)
    log("  created")

frappe.clear_cache()
log("  cache cleared")

log("")
log("4) item group tree (top-level groups used for gggg)")
roots = frappe.get_all("Item Group",
                       filters=[["parent_item_group", "in", ("", "All Item Groups")]],
                       fields=["name", "aig_group_number"], order_by="name")
for r in roots:
    log(f"  root={r.name!r} aig_group_number={r.aig_group_number}")
if not roots:
    log("  (no top-level groups found besides 'All Item Groups'?)")

grp_of_feed = frappe.db.get_value("Item", "AIG-INV-FEED", "item_group")
log(f"  AIG-INV-FEED item_group = {grp_of_feed!r}")

TEST_ITEMS = []


def make(code, group, uom="Nos"):
    doc = frappe.get_doc({
        "doctype": "Item", "item_code": code or None, "item_group": group,
        "item_name": "TEST auto-code", "stock_uom": uom,
        "is_stock_item": 1,
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    TEST_ITEMS.append(doc.name)
    return doc


def cleanup_all():
    for n in TEST_ITEMS:
        if n and frappe.db.exists("Item", n):
            frappe.delete_doc("Item", n, ignore_permissions=True, force=True)
            log(f"  deleted test item {n}")


results = []
try:
    log("")
    log("5) TEST A: empty item_code (expect AIG-gggg-0001, code==name)")
    d = make(None, grp_of_feed)
    results.append(("A", d.name, d.item_code))
    log(f"  name={d.name} item_code={d.item_code} group={d.item_group}")

    log("6) TEST B: second item same group (expect 0002)")
    d = make(None, grp_of_feed)
    results.append(("B", d.name, d.item_code))
    log(f"  name={d.name} item_code={d.item_code}")

    other = None
    for r in roots:
        if r.name != grp_of_feed:
            other = r.name
            break
    if other:
        log(f"7) TEST C: item in other group {other!r} (own prefix)")
        d = make(None, other)
        results.append(("C", d.name, d.item_code))
        log(f"  name={d.name} item_code={d.item_code}")

    log("8) TEST D: explicit code is respected (admin)")
    d = make("AIG-MANUAL-CHECK", grp_of_feed)
    results.append(("D", d.name, d.item_code))
    log(f"  name={d.name} item_code={d.item_code}")
except Exception:
    import traceback
    log("  TEST FAILED -- full traceback:")
    log(traceback.format_exc())
finally:
    log("")
    log("9) cleanup test items + reset touched counters/group numbers")
    frappe.set_user("Administrator")
    used_groups = set()
    for tag, name, code in results:
        if (code and len(code) == 13 and code.startswith("AIG-")
                and code.endswith(tuple("0123456789"))
                and code[4:8].isdigit() and code[9:13].isdigit()):
            g = code[4:8]
            row = frappe.db.get_value("Item Group", {"aig_group_number": int(g)},
                                      "name")
            if row:
                used_groups.add(row)
    cleanup_all()
    for g in sorted(used_groups):
        frappe.db.set_value("Item Group", g, "aig_group_seq", 0,
                            update_modified=False)
        if g != "AIG Inventory":  # demo group keeps its number 1
            frappe.db.set_value("Item Group", g, "aig_group_number", 0,
                                update_modified=False)
        log(f"  counters reset for group {g!r}")
    frappe.clear_cache()
    log("  cache cleared")

log("")
log("VERDICT: TESTS A-D above show the generated codes. Live demo now starts "
    "fresh at AIG-0001-0001 in the first group used.")
