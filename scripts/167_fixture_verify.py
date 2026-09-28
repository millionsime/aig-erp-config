# 167_fixture_verify.py -- READ-ONLY: confirm the two NEW fixture files carry
# the AIG rows (4 Print Formats, 7 Workspaces) and core counters are stable.
import frappe
import json

def log(*a):
    print(*a, flush=True)

base = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/fixtures/"

pf = json.load(open(base + "print_format.json"))
log("print_format.json rows:", len(pf))
for d in pf:
    log("  PF:", d.get("name"))

ws = json.load(open(base + "workspace.json"))
log("workspace.json rows:", len(ws))
for d in ws:
    log("  WS:", d.get("name"))

log("custom_field.json rows:", len(json.load(open(base + "custom_field.json"))))
log("server_script.json rows:", len(json.load(open(base + "server_script.json"))))
log("workflow.json rows:", len(json.load(open(base + "workflow.json"))))
log("custom_docperm.json rows:", len(json.load(open(base + "custom_docperm.json"))))

log("")
log("Live DB counters (post-migrate should match):")
log("  Workflow:", frappe.db.count("Workflow"))
log("  Server Script:", frappe.db.count("Server Script"))
log("  Workspace AIG%:", frappe.db.count("Workspace", [["name", "like", "AIG%"]]))
log("  Print Format AIG%:", frappe.db.count("Print Format", [["name", "like", "AIG%"]]))
log("DONE")
