# AIG config - step 41: FIX child cost_center blocking Cost Center User Permissions.
#
# ROOT CAUSE (verified in step 40g):
#   Frappe's has_user_permission() checks EVERY Link field on the doc AND all child
#   rows against the user's allowed values. Material Request Item / Stock Entry
#   Detail auto-default their `cost_center` to the company default ("Main - AIG"),
#   which is NOT in an enterprise user's allowed Cost Centers. So even though the
#   header aig_cost_center is allowed, the child cost_center denies read/submit.
#   (create passed only because the child value is still empty at insert-time.)
#
# CONFIG-LAYER FIX (no core edits):
#   1. Property Setter: ignore_user_permissions=1 on the CHILD cost_center fields so
#      enterprise isolation is governed by the header aig_cost_center Link (which the
#      user sets and which stays inside their allowed Cost Centers). Header-level and
#      list-level isolation is unchanged.
#   2. Server Script: sync each item's cost_center to the header aig_cost_center so
#      accounting still posts to the correct enterprise cost center (not Head Office).
#   Both are pure config. Idempotent. Verifies has_permission at the end.
import frappe
import traceback

ABBR = "AIG"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def set_property_setter(doctype, fieldname, prop, value, ptype="Check"):
    """Idempotent DocField Property Setter (config layer, reversible)."""
    ps_name = f"{doctype}-{fieldname}-{prop}"
    if frappe.db.exists("Property Setter", {"name": ps_name}):
        ps = frappe.get_doc("Property Setter", ps_name)
        if str(ps.value) != str(value):
            ps.value = value
            ps.flags.ignore_permissions = True
            ps.save(ignore_permissions=True)
            log("UPDATE", f"Property Setter {ps_name} = {value}")
        else:
            log("EXISTS", f"Property Setter {ps_name}")
        return ps_name
    ps = frappe.get_doc({
        "doctype": "Property Setter",
        "name": ps_name,
        "doctype_or_field": "DocField",
        "doc_type": doctype,
        "field_name": fieldname,
        "property": prop,
        "property_type": ptype,
        "value": value,
        "module": "Custom",
    })
    ps.flags.ignore_permissions = True
    try:
        ps.insert(ignore_permissions=True)
        log("CREATE", f"Property Setter {ps_name} = {value}")
    except Exception:
        print(f"!! FAILED Property Setter {ps_name}")
        print(traceback.format_exc())
    return ps_name


def set_script(name, reference_doctype, doctype_event, script):
    if frappe.db.exists("Server Script", name):
        ss = frappe.get_doc("Server Script", name)
        if ss.script != script or ss.disabled or ss.doctype_event != doctype_event:
            ss.script = script
            ss.disabled = 0
            ss.doctype_event = doctype_event
            ss.reference_doctype = reference_doctype
            ss.script_type = "DocType Event"
            ss.flags.ignore_permissions = True
            ss.save(ignore_permissions=True)
            log("UPDATE", f"Server Script {name}")
        else:
            log("EXISTS", f"Server Script {name}")
        return name
    doc = frappe.get_doc({
        "doctype": "Server Script", "name": name, "script_type": "DocType Event",
        "reference_doctype": reference_doctype, "doctype_event": doctype_event,
        "script": script, "disabled": 0,
    })
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"Server Script {name}")
    except Exception:
        print(f"!! FAILED {name}")
        print(traceback.format_exc())
    return name


# ---------------------------------------------------------------- 1. Property Setters
# Child cost_center must not drive Cost Center user-permission matching; the header
# aig_cost_center Link does. This keeps enterprise isolation intact while allowing the
# child accounting cost center to be the enterprise default.
for dt in ["Material Request Item", "Stock Entry Detail"]:
    set_property_setter(dt, "cost_center", "ignore_user_permissions", 1, "Check")

# ---------------------------------------------------------------- 2. Cost center sync
MR_CC_SYNC = """# AIG - keep every request line on the requesting enterprise's cost center so
# accounting posts to the correct enterprise (never the Head Office default).
hdr = doc.get("aig_cost_center")
if hdr:
    for it in (doc.items or []):
        it.cost_center = hdr
"""
set_script("AIG - MR Item Cost Center Sync", "Material Request", "Before Save", MR_CC_SYNC)

SE_CC_SYNC = """# AIG - keep every stock-entry line on the enterprise cost center of the document
# so accounting posts to the correct enterprise (never the Head Office default).
hdr = doc.get("aig_cost_center")
if hdr:
    for it in (doc.items or []):
        it.cost_center = hdr
"""
set_script("AIG - SE Item Cost Center Sync", "Stock Entry", "Before Save", SE_CC_SYNC)

frappe.db.commit()
frappe.clear_cache(doctype="Material Request")
frappe.clear_cache(doctype="Stock Entry")
frappe.clear_cache(doctype="Material Request Item")
frappe.clear_cache(doctype="Stock Entry Detail")

# ---------------------------------------------------------------- 3. Verify
print("\n=== VERIFY: enduser.agro read/submit on a Dairy-Farm request ===")
U = "enduser.agro@aig.local"
DAIRY_CC = f"Dairy Farm - {ABBR}"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
ITEM = "AIG-INV-FEED"
verify_ok = None
try:
    frappe.set_user(U)
    mr = frappe.get_doc({
        "doctype": "Material Request", "company": "Adama Investment Group",
        "material_request_type": "Material Issue", "schedule_date": frappe.utils.today(),
        "aig_cost_center": DAIRY_CC,
        "items": [{"item_code": ITEM, "qty": 2, "warehouse": DAIRY_WH,
                   "schedule_date": frappe.utils.today()}],
    })
    mr.insert()
    frappe.db.commit()
    mr.reload()
    item_cc = [i.get("cost_center") for i in mr.items]
    r_read = frappe.has_permission("Material Request", ptype="read", doc=mr, throw=False)
    r_write = frappe.has_permission("Material Request", ptype="write", doc=mr, throw=False)
    r_submit = frappe.has_permission("Material Request", ptype="submit", doc=mr, throw=False)
    print("item cost_center after sync:", item_cc)
    print("has_permission read:", r_read, "write:", r_write, "submit:", r_submit)
    verify_ok = bool(r_read and r_submit)
    vname = mr.name
except Exception:
    print("VERIFY EXCEPTION:")
    print(traceback.format_exc())
    vname = None
finally:
    frappe.set_user("Administrator")

if vname:
    frappe.delete_doc("Material Request", vname, ignore_permissions=True, force=True)
    frappe.db.commit()

print(f"\nSTEP41_COMPLETE {len(LOG)} actions verify_ok={verify_ok}")


def run():
    frappe.db.commit()
    return f"{len(LOG)} actions, verify_ok={verify_ok}"
