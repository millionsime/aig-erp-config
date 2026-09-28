# 119_mr_defaults_dump.py -- 118 proved: new MRs get header
# aig_cost_center='Adama Investment Group - AIG' (root CC) which fails
# enduser.agro's doc-level read (her root-CC user permission is scoped to the
# Cost Center doctype only). Dump the MR server scripts + custom field defaults
# to find who injects the root CC. READ-ONLY.

import frappe


def log(*a):
    print(*a, flush=True)


log("1) MR SERVER SCRIPTS")
for name in ["AIG - MR Request Defaults", "AIG - MR Item Cost Center Sync",
             "AIG - MR End User Type Default", "AIG - MR End User Type Guard",
             "AIG - MR Approval Guard", "AIG - MR Stock Item Guard"]:
    if not frappe.db.exists("Server Script", name):
        continue
    meta = frappe.db.get_value("Server Script", name,
                               ["script_type", "disabled"], as_dict=True)
    log(f"--- {name} {meta} ---")
    log(frappe.db.get_value("Server Script", name, "script") or "(empty)")
    log("")

log("2) aig_cost_center CUSTOM FIELDS (defaults)")
for r in frappe.get_all("Custom Field",
                        filters={"fieldname": "aig_cost_center"},
                        fields=["dt", "default", "insert_after", "field_label"]):
    log(f"  {r}")

log("")
log("3) enduser.agro Cost Center User Permission rows (db order + modified)")
for r in frappe.get_all("User Permission",
                        filters={"user": "enduser.agro@aig.local",
                                 "allow": "Cost Center"},
                        fields=["for_value", "applicable_for",
                                "apply_to_all_doctypes", "modified"],
                        order_by="modified desc"):
    log(f"  {r}")
