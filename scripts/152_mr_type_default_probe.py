# 152_mr_type_default_probe.py -- READ-ONLY: why does Purpose default to
# "Material Issue"? Checks (1) DocType field default, (2) Property Setters,
# (3) custom fields, (4) user/global defaults, (5) server + client scripts
# touching material_request_type, and (6) reproduces the UI insert as
# enduser.agro with type Purchase, then reads back what landed in the DB
# (probe doc deleted immediately).
import frappe


def log(*a):
    print(*a, flush=True)


ENDUSER = "enduser.agro@aig.local"

log("1) DocType field definition")
f = frappe.get_meta("Material Request").get_field("material_request_type")
log(f"  default={f.default!r} options={f.options!r} "
    f"reqd={f.reqd} in_list_view={f.in_list_view}")

log("")
log("2) Property Setters on Material Request")
for p in frappe.get_all("Property Setter",
                        filters={"doc_type": "Material Request"},
                        fields=["property", "property_type", "field_name",
                                "value"]):
    log(f"  {p.field_name or '(doc)'}: {p.property} = {p.value!r}")

log("")
log("3) Custom Fields on MR with a default set")
for c in frappe.get_all("Custom Field",
                        filters={"dt": "Material Request"},
                        fields=["fieldname", "label", "default",
                                "fieldtype"]):
    if c.default not in (None, ""):
        log(f"  {c.fieldname} ({c.label}): default={c.default!r}")
log("  (full list count: "
    + str(frappe.db.count("Custom Field", {"dt": "Material Request"})) + ")")

log("")
log("4) user / global defaults for material_request_type")
log(f"  global default: {frappe.db.get_default('material_request_type')!r}")
log(f"  enduser default: "
    f"{frappe.defaults.get_user_default('material_request_type', ENDUSER)!r}")

log("")
log("5) scripts touching material_request_type")
for s in frappe.get_all("Server Script",
                        filters={"disabled": 0},
                        fields=["name", "reference_doctype", "doctype_event",
                                "script"]):
    if "material_request_type" in (s.script or ""):
        log(f"  SERVER {s.name} ({s.reference_doctype}/{s.doctype_event}):")
        for line in s.script.splitlines():
            if "material_request_type" in line:
                log(f"    | {line.strip()[:120]}")
for c in frappe.get_all("Client Script",
                        filters={"dt": "Material Request", "enabled": 1},
                        fields=["name", "script"]):
    if "material_request_type" in (c.script or ""):
        log(f"  CLIENT {c.name}:")
        for line in c.script.splitlines():
            if "material_request_type" in line:
                log(f"    | {line.strip()[:120]}")

log("")
log("6) REPRODUCE: insert as enduser with type Purchase (like the UI POST)")
name = None
frappe.set_user(ENDUSER)
try:
    d = frappe.get_doc({
        "doctype": "Material Request", "company": "Adama Investment Group",
        "material_request_type": "Purchase",
        "transaction_date": frappe.utils.nowdate(),
        "aig_cost_center": "Animal Feed Factory - AIG",
        "aig_estimated_total": 900000,
        "items": [{"item_code": "AIG-DEMO-LAPTOP", "qty": 10, "uom": "Nos",
                   "schedule_date": frappe.utils.nowdate(), "rate": 80000,
                   "warehouse": "Animal Feed Plant - AIG"}],
    })
    d.insert()
    name = d.name
finally:
    frappe.set_user("Administrator")
if name:
    got = frappe.db.get_value("Material Request", name,
                              ["material_request_type", "workflow_state",
                               "owner"], as_dict=True)
    log(f"  created {name}: type in DB = {got.material_request_type!r} "
        f"state={got.workflow_state!r}")
    frappe.delete_doc("Material Request", name, force=True,
                      ignore_permissions=True)
    log("  (probe doc deleted)")
log("DONE 152")
