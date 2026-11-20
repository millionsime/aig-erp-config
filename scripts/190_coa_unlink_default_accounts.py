# Run BEFORE 83_import_coa.py on a site that still has ERPNext's default chart.
# The Chart of Accounts Importer deletes the default accounts, and refuses when
# anything links to them ("Cannot delete or cancel because Account X is linked
# with ..."). This clears every link we have met, then reports any left.
# Everything removed here is rebuilt after the import by 84/86/191/192 and
# custom_theme.aig_custom_theme.setup.ensure_tax_setup.run.
import frappe

company = "Adama Investment Group"

# 1. child rows that point at default accounts
for dt in ("Expense Claim Account", "Mode of Payment Account"):
    if frappe.db.table_exists(dt):
        frappe.db.sql(f"delete from `tab{dt}` where company=%s", company)
        print("cleared", dt)

# 2. tax templates (re-created by ensure_tax_setup)
for dt in ("Item Tax Template", "Sales Taxes and Charges Template",
           "Purchase Taxes and Charges Template"):
    for n in frappe.get_all(dt, filters={"company": company}, pluck="name"):
        try:
            frappe.delete_doc(dt, n, force=True)
            print("deleted", dt, n)
        except Exception as e:
            print("could not delete", dt, n, str(e)[:120])

# 3. report anything else still linked to an account of this company
accts = tuple(frappe.get_all("Account", filters={"company": company}, pluck="name")) or ("",)
skip = {"Account", "GL Entry", "Company", "Account Closing Balance", "Chart of Accounts Importer"}
fields = frappe.get_all("DocField", filters={"fieldtype": "Link", "options": "Account"},
                        fields=["parent", "fieldname"])
fields += frappe.get_all("Custom Field", filters={"fieldtype": "Link", "options": "Account"},
                         fields=["dt as parent", "fieldname"])
left = 0
for f in fields:
    if f.parent in skip:
        continue
    meta = frappe.get_meta(f.parent)
    if meta.issingle or meta.is_virtual or not frappe.db.table_exists(f.parent):
        continue
    rows = frappe.db.sql(
        f"select name from `tab{f.parent}` where `{f.fieldname}` in %s limit 5", [accts])
    if rows:
        left += 1
        print("STILL LINKED:", f.parent, f.fieldname, [r[0] for r in rows])

frappe.db.commit()
print("done; remaining links:", left, "(0 = safe to run 83_import_coa.py)")
