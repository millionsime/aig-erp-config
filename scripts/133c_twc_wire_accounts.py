# 133c_twc_wire_accounts.py -- Section 4.2: make withholding actually POST.
# v16 facts (verified in source):
#   - posting account comes from Tax Withholding Category.accounts (company,
#     account) rows; get_company_account(company) throws without one.
#   - a Tax Withholding Group bundles several categories; Supplier carries
#     tax_withholding_category OR tax_withholding_group; PI auto-sets
#     apply_tds and computes the withheld rows; PE copies the fields from the
#     supplier and generates tax_withholding_entries.
# This script adds the missing account rows (2132 VAT WH, 2133 WHT), creates
# the group with both categories, and defaults it on all demo suppliers.

import frappe


def log(*a):
    print(*a, flush=True)


COMPANY = "Adama Investment Group"
GROUP_NAME = "AIG Supplier Withholding"

log("1) account rows on the two TWC categories")
wants = [("AIG 7.5% VAT Withholding", "2132 - VAT Withholding Payable - AIG"),
         ("AIG 3% Withholding Tax", "2133 - Withholding Tax Payable - AIG")]
for cat, acct in wants:
    if not frappe.db.exists("Account", acct):
        alt = frappe.get_all("Account", filters={"company": COMPANY,
                                                 "name": ["like", f"{acct.split(' - ')[0]}%"]},
                             pluck="name")
        if not alt:
            log(f"  !! account missing for {cat}: expected {acct!r}, no fallback found")
            continue
        acct = alt[0]
        log(f"  (using resolved account {acct!r} for {cat})")
    d = frappe.get_doc("Tax Withholding Category", cat)
    has = any(a.company == COMPANY for a in (d.get("accounts") or []))
    if has:
        log(f"  {cat}: account row exists ({[a.account for a in d.accounts]})")
        continue
    d.append("accounts", {"company": COMPANY, "account": acct})
    d.flags.ignore_permissions = True
    d.save(ignore_permissions=True)
    log(f"  {cat}: account row added -> {acct}")

log("")
log("2) Tax Withholding Group bundling both categories")
if not frappe.db.exists("Tax Withholding Group", GROUP_NAME):
    grp_meta = frappe.get_meta("Tax Withholding Group")
    table_fields = [f for f in grp_meta.fields if f.fieldtype == "Table"]
    if not table_fields:
        log("  !! Tax Withholding Group has no child table field - cannot bundle")
        raise SystemExit(1)
    tf = table_fields[0]
    child_meta = frappe.get_meta(tf.options)
    link_field = next(f.fieldname for f in child_meta.fields
                      if f.fieldtype == "Link" and f.options == "Tax Withholding Category")
    log(f"  group child table: {tf.options} (link field {link_field!r})")
    doc = {"doctype": "Tax Withholding Group", "group_name": GROUP_NAME}
    doc[tf.fieldname] = [{link_field: "AIG 7.5% VAT Withholding"},
                         {link_field: "AIG 3% Withholding Tax"}]
    frappe.get_doc(doc).insert(ignore_permissions=True)
    log(f"  group created: {GROUP_NAME}")
else:
    log(f"  group exists: {GROUP_NAME}")

log("")
log("3) default the group on demo suppliers")
suppliers = frappe.get_all("Supplier", filters={"company": COMPANY},
                           pluck="name")
for s in suppliers:
    cur_group = frappe.db.get_value("Supplier", s, "tax_withholding_group")
    cur_cat = frappe.db.get_value("Supplier", s, "tax_withholding_category")
    if cur_group or cur_cat:
        log(f"  {s}: already set (group={cur_group!r}, category={cur_cat!r})")
        continue
    frappe.db.set_value("Supplier", s, "tax_withholding_group", GROUP_NAME,
                        update_modified=False)
    log(f"  {s}: tax_withholding_group = {GROUP_NAME!r}")

log("")
log("4) record facts")
pe_meta = frappe.get_meta("Payment Entry")
for fn in ("tax_withholding_category", "tax_withholding_group",
           "tax_withholding_entries", "apply_tds",
           "override_tax_withholding_entries"):
    f = pe_meta.get_field(fn)
    log(f"  PE.{fn}: {'present' if f else 'MISSING'}")
pi_meta = frappe.get_meta("Purchase Invoice")
f = pi_meta.get_field("tax_withholding_category")
log(f"  PI.tax_withholding_category: {'present' if f else 'MISSING (engine uses supplier default)'}")

frappe.clear_cache()
log("")
log("DONE 133c")
