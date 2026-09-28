# AIG foundation - BUILD D: Cost Center mandatory on transactions (config layer).
#
# v16 reality (verified in source):
#  - The old "Allow Cost Center In Entries of Balance Sheet Account" setting no
#    longer exists; tagging BS accounts with a Cost Center is always allowed.
#  - GL engine enforces CC only on P&L accounts. BS coverage is our job:
#      * JE: rows carry their own cost_center into GL (no header cascade)
#      * PE: header cost_center flows to all PE GL rows
#      * SI/PI: item rows carry cost_center (auto-default header -> company)
#  - Accounting Dimension cannot be used for Cost Center (core forbids it), so
#    enforcement = Property Setter (reqd) + Before Validate Server Scripts.
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

COMPANY = "Adama Investment Group"

# ---------------------------------------------------------------- property setters
ps = [
    ("Payment Entry", None, "cost_center", "reqd", 1),
    ("Sales Invoice", None, "cost_center", "reqd", 1),
    ("Sales Invoice Item", None, "cost_center", "reqd", 1),
    ("Purchase Invoice", None, "cost_center", "reqd", 1),
    ("Purchase Invoice Item", None, "cost_center", "reqd", 1),
    ("Journal Entry Account", None, "cost_center", "reqd", 1),
]
for dt, fn, field, prop, val in ps:
    make_property_setter(dt, field, prop, val, "Check", validate_fields_for_doctype=False)
    print("PS:", dt + "." + field, prop, "=", val)

# Make PE cost center visible (core hides it in v16)
pe_hidden = frappe.get_meta("Payment Entry").get_field("cost_center")
print("PE cost_center hidden flag (core):", pe_hidden.hidden)
if pe_hidden.hidden:
    make_property_setter("Payment Entry", "cost_center", "hidden", 0, "Check")
    print("PS: Payment Entry.cost_center hidden = 0")

# ---------------------------------------------------------------- server scripts
JE_GUARD = """# AIG: every Journal Entry line must carry a Cost Center.
# Rows default from the header, then from the Company default; a line that
# would still post without one is blocked. (Config layer - no core edits.)
company_cc = None
if doc.company:
    company_cc = frappe.db.get_value("Company", doc.company, "cost_center")  # v16 default-CC fieldname
for row in (doc.get("accounts") or []):
    if not row.get("cost_center"):
        cc = doc.get("cost_center") or company_cc
        if cc:
            row.cost_center = cc
for row in (doc.get("accounts") or []):
    if not row.get("cost_center"):
        frappe.throw("AIG: Cost Center is required on Journal Entry row for account " + str(row.get("account")))
"""

PE_GUARD = """# AIG: Payment Entry must carry a Cost Center (flows to all its GL rows).
if not doc.get("cost_center"):
    cc = frappe.db.get_value("Company", doc.company, "cost_center")  # v16 default-CC fieldname
    if cc:
        doc.cost_center = cc
if not doc.get("cost_center"):
    frappe.throw("AIG: Cost Center is required on Payment Entry for enterprise-level Balance Sheet tracking.")
"""

def inv_guard(label):
    return """# AIG: Sales/Purchase Invoice must carry a Cost Center on header and items.
if not doc.get("cost_center"):
    cc = frappe.db.get_value("Company", doc.company, "cost_center")  # v16 default-CC fieldname
    if cc:
        doc.cost_center = cc
for row in (doc.get("items") or []):
    if not row.get("cost_center") and doc.get("cost_center"):
        row.cost_center = doc.get("cost_center")
for row in (doc.get("taxes") or []):
    if not row.get("cost_center") and doc.get("cost_center"):
        row.cost_center = doc.get("cost_center")
missing = []
for row in (doc.get("items") or []):
    if not row.get("cost_center"):
        missing.append(str(row.get("item_code") or row.idx))
if missing:
    frappe.throw("AIG: Cost Center is required on """ + label + """ item rows: " + ", ".join(missing))
if not doc.get("cost_center"):
    frappe.throw("AIG: Cost Center is required on """ + label + """ for enterprise-level Balance Sheet tracking.")
"""

scripts = [
    ("AIG - CC Guard Journal Entry", "Journal Entry", "Before Validate", JE_GUARD),
    ("AIG - CC Guard Payment Entry", "Payment Entry", "Before Validate", PE_GUARD),
    ("AIG - CC Guard Sales Invoice", "Sales Invoice", "Before Validate", inv_guard("Sales Invoice")),
    ("AIG - CC Guard Purchase Invoice", "Purchase Invoice", "Before Validate", inv_guard("Purchase Invoice")),
]
for name, dt, event, body in scripts:
    if frappe.db.exists("Server Script", name):
        s = frappe.get_doc("Server Script", name)
        s.script = body
        s.disabled = 0
        s.save()
        print("UPDATED Server Script:", name)
    else:
        frappe.get_doc({
            "doctype": "Server Script",
            "name": name,
            "script_type": "DocType Event",
            "reference_doctype": dt,
            "doctype_event": event,
            "script": body,
            "disabled": 0,
        }).insert()
        print("CREATED Server Script:", name, f"({dt} / {event})")

# ------------------------------------------------- backfill draft demo payment
pe = frappe.db.get_value("Payment Entry", {"docstatus": 0}, "name")
if pe:
    row = frappe.db.get_value("Payment Entry", pe, ["cost_center", "company"], as_dict=True)
    if not row.cost_center:
        frappe.db.set_value("Payment Entry", pe, "cost_center", "Head Office - AIG")
        print("BACKFILLED draft Payment Entry", pe, "-> Head Office - AIG")
    else:
        print("draft PE already has CC:", pe, row.cost_center)

# ---------------------------------------------------------------- verification
print("\nVERIFY: Property Setters live in meta?")
for dt, field in [("Payment Entry", "cost_center"), ("Sales Invoice", "cost_center"),
                  ("Sales Invoice Item", "cost_center"), ("Purchase Invoice", "cost_center"),
                  ("Purchase Invoice Item", "cost_center"), ("Journal Entry Account", "cost_center")]:
    f = frappe.get_meta(dt).get_field(field)
    print(f"  {dt}.{field} reqd={f.reqd} hidden={f.hidden}")

print("\nVERIFY: Server Scripts present & enabled (disabled=0)?")
for s in frappe.get_all("Server Script", filters={"name": ["like", "AIG - CC Guard%"]},
                        fields=["name", "reference_doctype", "doctype_event", "disabled"]):
    print("  ", s)

print("\nDONE-D")
