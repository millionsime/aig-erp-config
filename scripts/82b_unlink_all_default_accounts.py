import frappe

company = "Adama Investment Group"
accts = set(frappe.get_all("Account", filters={"company": company}, pluck="name"))

# 1. Remove tax templates for this company (re-created later by ensure_tax_setup)
for dt in ["Item Tax Template", "Sales Taxes and Charges Template",
           "Purchase Taxes and Charges Template", "Tax Category"]:
    if dt == "Tax Category":
        continue
    for n in frappe.get_all(dt, filters={"company": company}, pluck="name"):
        try:
            frappe.delete_doc(dt, n, force=True)
            print("deleted", dt, n)
        except Exception as e:
            print("could not delete", dt, n, str(e)[:120])

# 2. Scan every Link field pointing to Account and report what still uses a default account
skip = {"Account", "GL Entry", "Company", "Account Closing Balance", "Chart of Accounts Importer"}
fields = frappe.get_all("DocField", filters={"fieldtype": "Link", "options": "Account"},
                        fields=["parent", "fieldname"])
fields += frappe.get_all("Custom Field", filters={"fieldtype": "Link", "options": "Account"},
                         fields=["dt as parent", "fieldname"])
for f in fields:
    if f.parent in skip:
        continue
    try:
        if not frappe.get_meta(f.parent).istable and frappe.get_meta(f.parent).issingle:
            continue
        rows = frappe.db.sql(
            f"select name from `tab{f.parent}` where `{f.fieldname}` in %s limit 5",
            [tuple(accts)] if accts else [("",)])
        if rows:
            print("STILL LINKED:", f.parent, f.fieldname, [r[0] for r in rows])
    except Exception:
        pass

frappe.db.commit()
print("done")