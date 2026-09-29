# 178_deployment_export.py -- Final deployment export (commits on success):
# 1) export the 3 custom DocTypes into their app folder (canonical
#    frappe.modules.export_file mechanism -- travels with the app, not DB)
# 2) add Workflow State / Workflow Action Master to the fixture list
# 3) re-export fixtures
import frappe
import subprocess

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")

# ------------------------------------------------ 1. DocType export
log("== 1. export custom DocTypes into app folders")
from frappe.modules.export_file import export_to_files
for dt in ["AIG Committee Signoff", "AIG Stock Migration Batch",
           "AIG Stock Migration Row"]:
    if not frappe.db.exists("DocType", dt):
        log("   SKIP (missing):", dt)
        continue
    module = frappe.db.get_value("DocType", dt, "module")
    log(f"   {dt}: module={module}")
    export_to_files(record_list=[("DocType", dt)])
    log("   exported:", dt)

# ------------------------------------------------ 2. fixtures list
log("== 2. add Workflow State / Action Master to fixtures")
hooks_path = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/hooks.py"
with open(hooks_path) as f:
    hooks = f.read()
addition = ('\t{"dt": "Workflow State", '
            '"filters": [["name", "in", ["Pending Head Approval"]]]},\n'
            '\t{"dt": "Workflow Action Master", '
            '"filters": [["name", "in", ["Submit Purchase Request", '
            '"Approve & Assign"]]]},\n]\n')
old_tail = "]\n"
marker = '\t{"dt": "Workspace", "filters": [["name", "like", "AIG%"]]},\n'
if "Workflow Action Master" not in hooks:
    if marker not in hooks:
        raise Exception("hooks.py marker not found - inspect manually")
    hooks = hooks.replace(marker, marker + addition)
    with open(hooks_path, "w") as f:
        f.write(hooks)
    log("   fixtures list extended")
else:
    log("   already present")

# ------------------------------------------------ 3. re-export fixtures
log("== 3. bench export-fixtures")
out = subprocess.run(
    ["bash", "-c", "cd /home/frappe/frappe-bench && "
     "bench --site frontend export-fixtures 2>&1 | tail -4"],
    capture_output=True, text=True)
log(out.stdout or out.stderr)

# ------------------------------------------------ 4. verify
log("== 4. verify")
import json
ws_path = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/fixtures/workflow_state.json"
try:
    log("   workflow_state.json:", [d["name"] for d in json.load(open(ws_path))])
except Exception as e:
    log("   workflow_state.json:", e)
wa_path = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/fixtures/workflow_action_master.json"
try:
    log("   workflow_action_master.json:", [d["name"] for d in json.load(open(wa_path))])
except Exception as e:
    log("   workflow_action_master.json:", e)
log("DONE 178")
