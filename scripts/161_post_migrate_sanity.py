# 161_post_migrate_sanity.py -- READ-ONLY: after `bench migrate` (which
# re-synced fixtures), confirm the config counts and that the three key
# guards are still live in the Server Scripts.
import frappe


def log(*a):
    print(*a, flush=True)


log("server scripts: " + str(frappe.db.count("Server Script")))
log("workflows: " + str(frappe.db.count("Workflow")))
log("custom fields: " + str(frappe.db.count("Custom Field")))
log("custom docperms: " + str(frappe.db.count("Custom DocPerm")))
wh = frappe.db.get_value("Server Script",
                         "AIG - Payment Withholding 7.5% + 3%", "script")
log("withholder guard live: "
    + str("double-withholding guard" in (wh or "")))
nm = frappe.db.get_value("Server Script", "AIG - MR CC Normalize", "script")
log("normalize guard live: "
    + str("no cost center could be derived" in (nm or "")))
maj = frappe.db.get_value("Server Script",
                          "AIG - PO Committee Majority", "script")
log("click-approval live: "
    + str("on behalf of all" in (maj or "")))
rg = frappe.db.get_value("Server Script",
                         "AIG - PO Committee Reject Guard", "script")
log("reject guard live: "
    + str("Record your 'Reject' sign-off first" in (rg or "")))
log("DONE 161")
