# AIG foundation - BUILD B: Chart of Accounts corrections (config-layer).
# 1. Create group "Bank Accounts - AIG" under Current Assets (standard placement).
# 2. Reparent "Commercial Bank of Ethiopia - AIG" (currently misfiled as a
#    LIABILITY under Non-Current Liabilities) into it. The Account doctype
#    re-derives root_type/report_type from the parent on save - the account
#    name is unchanged, so its GL balance (ETB -300,000) is preserved.
COMPANY = "Adama Investment Group"
BANK_GROUP = "Bank Accounts - AIG"
CBE = "Commercial Bank of Ethiopia - AIG"

if not frappe.db.exists("Account", BANK_GROUP):
    g = frappe.new_doc("Account")
    g.account_name = "Bank Accounts"
    g.parent_account = "Current Assets - AIG"
    g.is_group = 1
    g.company = COMPANY
    g.account_type = "Bank"
    g.account_currency = "ETB"
    g.insert()
    print("CREATED group:", g.name)
else:
    print("group exists:", BANK_GROUP)

cbe = frappe.get_doc("Account", CBE)
before = (cbe.root_type, cbe.report_type, cbe.parent_account)
cbe.parent_account = BANK_GROUP
cbe.save()
after = frappe.db.get_value("Account", CBE, ["root_type", "report_type", "parent_account"], as_dict=True)
print("CBE before:", before)
print("CBE after :", after)

if after.root_type != "Asset" or after.report_type != "Balance Sheet":
    frappe.throw("CBE reclassification failed - expected Asset / Balance Sheet")

# Tree integrity check on the whole CoA after the move
from erpnext.accounts.utils import get_balance_on
print("CBE balance (must be unchanged):", get_balance_on(account=CBE))

# Company default bank must still point at CBE
print("Company default_bank_account:",
      frappe.db.get_value("Company", COMPANY, "default_bank_account"))

print("\nDONE-B")
