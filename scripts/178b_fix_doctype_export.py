# 178b_fix_doctype_export.py -- CORRECTIVE (commits on success):
# 1) point the 3 custom DocTypes' module at "AIG Custom Theme" (custom_theme
#    is the installed carrier app; erpnext/custom_app folders were wrong)
# 2) delete the stray JSON folders exported into erpnext + custom_app trees
# 3) repair hooks.py fixtures list (the 178 patch double-closed the list)
#    by patching the WSL source, copying it in, syntax-checking
# 4) re-export the DocTypes (now into custom_theme/custom_theme/...) and
#    re-export fixtures
import frappe
import subprocess
import shutil
import os
import ast

def log(*a):
    print(*a, flush=True)

frappe.set_user("Administrator")

# ------------------------------------ 1. DocType module -> AIG Custom Theme
log("== 1. re-module DocTypes to AIG Custom Theme")
for dt in ["AIG Committee Signoff", "AIG Stock Migration Batch",
           "AIG Stock Migration Row"]:
    frappe.db.set_value("DocType", dt, "module", "AIG Custom Theme")
    mod = frappe.db.get_value("DocType", dt, "module")
    log("  ", dt, "->", mod)

# --------------------------------------------- 2. remove stray export dirs
log("== 2. delete stray export folders (wrong apps)")
strays = [
    "/home/frappe/frappe-bench/apps/erpnext/erpnext/stock/doctype/"
    "aig_stock_migration_batch",
    "/home/frappe/frappe-bench/apps/erpnext/erpnext/stock/doctype/"
    "aig_stock_migration_row",
    "/home/frappe/frappe-bench/apps/custom_app/custom_app/aig_hr/doctype/"
    "aig_committee_signoff",
]
for p in strays:
    if os.path.isdir(p):
        shutil.rmtree(p)
        log("   removed:", p)
    else:
        log("   absent:", p)

# ------------------------------------------ 3. repair hooks.py (container path)
log("== 3. repair hooks.py fixtures list (in container)")
ct_hooks = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/hooks.py"
with open(ct_hooks) as f:
    src = f.read()
# undo any previous bad patch: collapse the broken tail back to a single ']\n'
bad = ('\t{"dt": "Workflow State", '
       '"filters": [["name", "in", ["Pending Head Approval"]]]},\n'
       '\t{"dt": "Workflow Action Master", '
       '"filters": [["name", "in", ["Submit Purchase Request", '
       '"Approve & Assign"]]]},\n]\n]\n')
good = ('\t{"dt": "Workflow State", '
        '"filters": [["name", "in", ["Pending Head Approval"]]]},\n'
        '\t{"dt": "Workflow Action Master", '
        '"filters": [["name", "in", ["Submit Purchase Request", '
        '"Approve & Assign"]]]},\n]\n')
if bad in src:
    src = src.replace(bad, good)
elif good not in src:
    # not patched yet or already different: insert before the final ']'
    marker = '\t{"dt": "Workspace", "filters": [["name", "like", "AIG%"]]},\n'
    if marker not in src:
        raise Exception("hooks.py marker not found - inspect manually")
    src = src.replace(marker, marker + good[len(marker):])
# syntax check BEFORE deploying
ast.parse(src)
with open(ct_hooks, "w") as f:
    f.write(src)
log("   container hooks.py repaired + parses")

# --------------------------------- 4. re-export DocTypes + fixtures
log("== 4. re-export into custom_theme")
from frappe.modules.export_file import export_to_files
for dt in ["AIG Committee Signoff", "AIG Stock Migration Batch",
           "AIG Stock Migration Row"]:
    export_to_files(record_list=[("DocType", dt)])
    log("   exported:", dt)
out = subprocess.run(
    ["bash", "-c", "cd /home/frappe/frappe-bench && "
     "bench --site frontend export-fixtures 2>&1 | tail -3"],
    capture_output=True, text=True)
log(out.stdout or out.stderr)

# ------------------------------------------------------- 5. verify
log("== 5. verify")
base = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/"
import json
for f in ["fixtures/workflow_state.json", "fixtures/workflow_action_master.json"]:
    p = base + f
    try:
        log("  ", f, [d["name"] for d in json.load(open(p))])
    except Exception as e:
        log("  ", f, "MISSING", e)
ct = base + "custom_theme/"
for d in ["aig_committee_signoff", "aig_stock_migration_batch",
          "aig_stock_migration_row"]:
    log("   doctype folder:", d, os.path.isdir(ct + d))
log("DONE 178b")
