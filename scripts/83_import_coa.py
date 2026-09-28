# 83_import_coa.py -- Import AIG's new Chart of Accounts via ERPNext's own
# erpnext.accounts.doctype.chart_of_accounts_importer.import_coa(), as
# Administrator. This is exactly what the Importer UI does (gate check ->
# unset_existing_data -> create_charts -> set_default_accounts), so defaults
# that ERPNext can auto-detect are set by ERPNext itself.
#
# Prereq: 80/81 purge + preflight done (validate_company passes).
# NOTE: wiring/verification only AFTER a successful import_coa -- anything
# after a failed import would roll the import back, so failures here abort.

import frappe
from frappe.utils.file_manager import save_file

COMPANY = "Adama Investment Group"
FILE_PATH = "/tmp/AIG_Corrected_Demo_CoA.csv"


def log(*a):
    print(*a, flush=True)


from erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer import (
    import_coa,
    validate_company,
)

log("STEP 1: importer gate")
validate_company(COMPANY)
log("  validate_company passed")

before = frappe.db.count("Account", {"company": COMPANY})
log(f"  accounts before: {before}")

log("STEP 2: register CSV as File doc")
with open(FILE_PATH, "rb") as f:
    content = f.read()
file_doc = save_file(
    "AIG_Corrected_Demo_CoA.csv",
    content,
    "Chart of Accounts Importer",
    COMPANY,
    folder="Home",
    is_private=1,
)
log(f"  File created: {file_doc.name} url={file_doc.file_url}")

log("STEP 3: import_coa (Administrator)")
frappe.set_user("Administrator")
try:
    import_coa(file_doc.file_url, COMPANY)
except frappe.PermissionError:
    # only_for("Accounts Manager") gate -- grant the role to Administrator
    u = frappe.get_doc("User", "Administrator")
    if "Accounts Manager" not in [r.role for r in u.get("roles", [])]:
        u.append("roles", {"role": "Accounts Manager"})
        u.flags.ignore_permissions = True
        u.save()
        log("  granted 'Accounts Manager' role to Administrator, retrying")
    import_coa(file_doc.file_url, COMPANY)
log("  import_coa returned OK")

# ------------------------------------------------------------ report
log("=" * 70)
after = frappe.db.count("Account", {"company": COMPANY})
log(f"STEP 4: accounts after import: {before} -> {after}")

roots = frappe.get_all(
    "Account",
    filters={"company": COMPANY, "parent_account": ("is", "not set")},
    fields=["name", "root_type", "account_type"],
    order_by="name",
)
log("  root accounts:")
for r in roots:
    log(f"    {r.name}  ({r.root_type})")

log("  spot checks:")
for label, filt in [
    ("AIG CBE bank", {"account_number": "1110.12"}),
    ("VAT Payable 15%", {"account_number": "2131"}),
    ("Trade Creditors control", {"account_number": "2101"}),
    ("Trade Debtors control", {"account_number": "1201"}),
    ("Depreciation group", {"account_number": "5700"}),
]:
    row = frappe.db.get_value(
        "Account",
        {"company": COMPANY, "account_number": filt["account_number"]},
        ["name", "account_type", "is_group"],
        as_dict=1,
    )
    log(f"    {label}: {row.name if row else '!! MISSING'} type={row.account_type if row else '-'} group={row.is_group if row else '-'}")

gle = frappe.db.count("GL Entry", {"company": COMPANY})
log(f"  GL Entry rows after import: {gle} (must be 0)")
if gle:
    raise RuntimeError("GL entries appeared during import -- investigate")

comp_fields = [
    r[0]
    for r in frappe.db.sql(
        """
        select df.fieldname from `tabDocField` df
        where df.parent = 'Company' and df.fieldtype = 'Link' and df.options = 'Account'
        union
        select cf.fieldname from `tabCustom Field` cf
        where cf.dt = 'Company' and cf.fieldtype = 'Link' and cf.options = 'Account'
        """,
    )
]
comp = frappe.db.get_value("Company", COMPANY, comp_fields, as_dict=1)
log("  Company account fields (auto-set by set_default_accounts / previously set):")
for k in sorted(comp or {}):
    v = comp[k]
    if v:
        log(f"    {k}: {v}")

log("=" * 70)
log("IMPORT COMPLETE")
