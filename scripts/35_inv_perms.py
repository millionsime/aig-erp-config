# AIG config - step 35: INVENTORY permissions (Custom DocPerm, config layer).
# Least privilege + separation of duties for the inventory roles across the stock
# doctypes. Uses the v16-correct "parent" field on Custom DocPerm and ORs new
# permissions into any existing row so the procurement demo's grants are preserved.
# NOTE: adding a Custom DocPerm flips a doctype to custom-permission mode, so every
# AIG role that needs access is listed explicitly (System Manager stays superuser).
import frappe

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def perm(dt, role, read=0, write=0, create=0, submit=0, cancel=0, amend=0,
         permlevel=0, print=None, email=None, export=None):
    """Create OR extend a Custom DocPerm row. Never reduces existing grants."""
    if print is None:
        print = read
    if email is None:
        email = read
    if export is None:
        export = read
    want = {"read": read, "write": write, "create": create, "submit": submit,
            "cancel": cancel, "amend": amend, "print": print, "email": email, "export": export}
    existing = frappe.db.get_value("Custom DocPerm",
                                   {"parent": dt, "role": role, "permlevel": permlevel},
                                   "*", as_dict=True)
    if existing:
        changed = False
        for k, v in want.items():
            if v and not existing.get(k):
                frappe.db.set_value("Custom DocPerm", existing.name, k, 1, update_modified=False)
                changed = True
        if changed:
            log("UPDATE", f"DocPerm {dt} -> {role} (L{permlevel}) extended")
        else:
            log("EXISTS", f"DocPerm {dt}/{role}/L{permlevel}")
        return
    vals = {"doctype": "Custom DocPerm", "parent": dt, "role": role, "permlevel": permlevel}
    for k, v in want.items():
        vals[k] = 1 if v else 0
    doc = frappe.get_doc(vals)
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    log("CREATE", f"DocPerm {dt} -> {role} (L{permlevel}) r{read}w{write}c{create}s{submit}x{cancel}")


INV_ADMIN = "AIG Inventory Administrator"
MAIN_STORE_ADMIN = "AIG Main Store Administrator"
GEN_STORE_KEEPER = "AIG General Store Keeper"
STORE_KEEPER = "AIG Store Keeper"
PROP_EXPERT = "AIG Property Admin Expert"
END_USER = "AIG End User"
AUDITOR = "AIG Internal Auditor"
ENT_HEAD = "AIG Enterprise Head"
FINANCE = "AIG Finance"

ALL_INV = [INV_ADMIN, MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, PROP_EXPERT, END_USER, AUDITOR]
READERS = [MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, PROP_EXPERT, END_USER, AUDITOR]

# ------------------------------------------------------------------ masters
perm("Item", INV_ADMIN, read=1, write=1, create=1)
perm("Item", PROP_EXPERT, read=1, write=1)          # assign bin / barcode / tag
for r in READERS:
    perm("Item", r, read=1)

perm("Item Group", INV_ADMIN, read=1, write=1, create=1)
for r in READERS:
    perm("Item Group", r, read=1)

for dt in ["UOM", "Brand"]:
    perm(dt, INV_ADMIN, read=1, write=1, create=1)
    for r in READERS:
        perm(dt, r, read=1)

perm("Warehouse", INV_ADMIN, read=1, write=1, create=1)
for r in [MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, PROP_EXPERT, AUDITOR]:
    perm("Warehouse", r, read=1)

perm("Cost Center", INV_ADMIN, read=1)
for r in [MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, END_USER, AUDITOR]:
    perm("Cost Center", r, read=1)

# Account read: opening stock docs under perpetual inventory loads accounts.
for r in [INV_ADMIN, MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, AUDITOR]:
    perm("Account", r, read=1)

# ---------------------------------------------------------------- Material Request (Model 19)
perm("Material Request", END_USER, read=1, write=1, create=1, submit=1, amend=1)
perm("Material Request", MAIN_STORE_ADMIN, read=1, write=1, submit=1, cancel=1)
perm("Material Request", ENT_HEAD, read=1, write=1, submit=1, cancel=1)
perm("Material Request", STORE_KEEPER, read=1, write=1)     # prepares the issue
perm("Material Request", GEN_STORE_KEEPER, read=1)
perm("Material Request", INV_ADMIN, read=1, write=1, create=1)
perm("Material Request", AUDITOR, read=1)
perm("Material Request", PROP_EXPERT, read=1)

# ---------------------------------------------------------------- Stock Entry (receive/issue/transfer)
perm("Stock Entry", STORE_KEEPER, read=1, write=1, create=1, submit=1)
perm("Stock Entry", GEN_STORE_KEEPER, read=1, write=1, create=1, submit=1, cancel=1)
perm("Stock Entry", MAIN_STORE_ADMIN, read=1, write=1, create=1, submit=1, cancel=1)
perm("Stock Entry", PROP_EXPERT, read=1, write=1)           # bins only, NO submit
perm("Stock Entry", INV_ADMIN, read=1, write=1, create=1, submit=1, cancel=1, amend=1)
perm("Stock Entry", AUDITOR, read=1)
perm("Stock Entry", END_USER, read=1)

# ---------------------------------------------------------------- Quality Inspection (Quality Form)
perm("Quality Inspection", STORE_KEEPER, read=1, write=1, create=1, submit=1, amend=1)
perm("Quality Inspection", GEN_STORE_KEEPER, read=1, write=1, submit=1)
perm("Quality Inspection", INV_ADMIN, read=1, write=1, create=1, submit=1)
perm("Quality Inspection", MAIN_STORE_ADMIN, read=1)
perm("Quality Inspection", PROP_EXPERT, read=1)
perm("Quality Inspection", AUDITOR, read=1)

# ---------------------------------------------------------------- Stock Reconciliation (counts/adjust)
# Separation of duties: preparer cannot submit; an approver submits.
perm("Stock Reconciliation", STORE_KEEPER, read=1, write=1, create=1)      # prepare only
perm("Stock Reconciliation", GEN_STORE_KEEPER, read=1, write=1, submit=1, cancel=1)
perm("Stock Reconciliation", MAIN_STORE_ADMIN, read=1, write=1, submit=1, cancel=1)
perm("Stock Reconciliation", INV_ADMIN, read=1, write=1, create=1, submit=1, cancel=1, amend=1)
perm("Stock Reconciliation", AUDITOR, read=1)

# ---------------------------------------------------------------- visibility / reports
for dt in ["Stock Ledger Entry", "Bin", "Batch", "Serial No"]:
    if frappe.db.exists("DocType", dt):
        for r in [INV_ADMIN, MAIN_STORE_ADMIN, GEN_STORE_KEEPER, STORE_KEEPER, AUDITOR]:
            perm(dt, r, read=1)

# Purchase Receipt read (receiving linked to a PO) for store roles
for r in [STORE_KEEPER, GEN_STORE_KEEPER, MAIN_STORE_ADMIN, AUDITOR]:
    perm("Purchase Receipt", r, read=1)

# Budget read for Main Store Administrator (reviews plan/budget information)
perm("Budget", MAIN_STORE_ADMIN, read=1)

# Finance / Inventory Accountant: valuation visibility (read) across stock docs
for dt in ["Stock Entry", "Stock Reconciliation", "Material Request", "Stock Ledger Entry", "Bin"]:
    perm(dt, FINANCE, read=1)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP35_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
