# 102_verify_row_cc_fix.py -- Verify the row-cost-center toast fix using the
# CORRECT permission wrapper (frappe.has_permission). Also extend the "AIG -
# SE Movement Defaults" server script so the document's enterprise cost center
# fills itself from the warehouse CC when the user leaves it blank.

import frappe

COMPANY = "Adama Investment Group"


def log(*a):
    print(*a, flush=True)


log("STEP 1: extend AIG - SE Movement Defaults (self-healing header CC)")
name = "AIG - SE Movement Defaults"
script = frappe.db.get_value("Server Script", name, "script") or ""
marker = 'self-heal: fill header aig_cost_center from warehouse CC'
if marker in script:
    log("  already extended")
else:
    if not script.endswith("\n"):
        script += "\n"
    script += (
        "\n"
        f"# {marker}\n"
        "if not doc.get(\"aig_cost_center\"):\n"
        "    doc.aig_cost_center = dst_cc or src_cc\n"
    )
    frappe.db.set_value("Server Script", name, "script", script)
    s = frappe.get_doc("Server Script", name)
    s.reload()
    s.flags.ignore_permissions = True
    s.save(ignore_permissions=True)
    log("  appended self-heal lines")

log("")
log("STEP 2: clear cache")
frappe.clear_cache()

log("")
log("STEP 3: VERIFY with the correct wrapper (frappe.has_permission)")
U = "storekeeper.agro@aig.local"

CASES = [
    ("SE row CC = Head Office (what ERPNext injects)", "Head Office - AIG"),
    ("SE row CC = Dairy Farm (after scrub)", "Dairy Farm - AIG"),
    ("SE row CC = empty (scrubber target before CC chosen)", None),
]
for label, cc in CASES:
    frappe.set_user(U)
    doc = frappe.new_doc("Stock Entry")
    doc.company = COMPANY
    doc.stock_entry_type = "Material Receipt"
    doc.purpose = "Material Receipt"
    doc.to_warehouse = "Dairy Farm Store - AIG"
    doc.aig_cost_center = "Dairy Farm - AIG" if cc else None
    doc.append("items", {"item_code": "AIG-INV-FEED", "qty": 1, "basic_rate": 40,
                         "t_warehouse": "Dairy Farm Store - AIG",
                         **({"cost_center": cc} if cc else {})})
    doc.name = "new-stock-entry-evkvhxjiqj"
    try:
        frappe.has_permission(doc, "read", user=U, throw=True)
        log(f"  {label}: READ OK")
    except Exception:
        log(f"  {label}: READ FAIL")

frappe.set_user("enduser.agro@aig.local")
mr = frappe.new_doc("Material Request")
mr.company = COMPANY
mr.material_request_type = "Material Issue"
mr.schedule_date = frappe.utils.today()
mr.append("items", {"item_code": "AIG-INV-FEED", "qty": 1,
                    "warehouse": "Dairy Farm Store - AIG",
                    "schedule_date": frappe.utils.today(),
                    "cost_center": "Head Office - AIG"})
mr.name = "new-material-request-probe000"
try:
    frappe.has_permission(mr, "read", user="enduser.agro@aig.local", throw=True)
    log("  MR row CC = Head Office (raw, no scrub): READ OK (unexpected!)")
except Exception:
    log("  MR row CC = Head Office (raw, no scrub): READ FAIL (expected; Client Script scrubs it in the UI)")
frappe.set_user("Administrator")

log("")
log("STEP 4: enabled Client Scripts (the UI-side fix)")
for cs in frappe.get_all("Client Script",
                         filters={"dt": ("in", ["Stock Entry", "Material Request", "Purchase Order"])},
                         fields=["name", "enabled"]):
    log(f"  {cs.name}: {'enabled' if cs.enabled else 'DISABLED'}")

log("")
log("DONE -- user must hard-refresh (Ctrl+Shift+R) to load the new Client Scripts.")
