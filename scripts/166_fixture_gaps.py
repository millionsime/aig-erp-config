# 166_fixture_gaps.py -- READ-ONLY: find config doctypes with AIG-owned rows
# that the fixture set does NOT yet capture (gap analysis for "build more
# fixtures if necessary"). Creates nothing, deletes nothing.
import frappe
import json

def log(*a):
    print(*a, flush=True)

log("=== 1. AIG-owned rows in doctypes NOT in the fixture list ===")
gap_doctypes = [
    ("Print Format", "name like 'AIG%' or owner like '%aig.local' or modified_by like '%aig.local'"),
    ("Workspace", "label like 'AIG%' or name like 'aig%'"),
    ("Number Card", "label like 'AIG%'"),
    ("Dashboard Chart", "name like 'AIG%'"),
    ("Letter Head", "name like 'AIG%'"),
    ("Email Template", "name like 'AIG%'"),
    ("Custom Translation", "1=1"),
    ("Translation", "1=1"),
    ("Role Profile", "1=1"),
    ("User", "name like '%aig.local'"),
    ("Company", "1=1"),
]
for dt, cond in gap_doctypes:
    try:
        n = frappe.db.count(dt, [cond]) if frappe.db.exists("DocType", dt) else -1
        log(f"{dt}: {n}")
    except Exception as e:
        log(f"{dt}: ERR {e}")

log("")
log("=== 2. Print Formats (any owner) ===")
for r in frappe.db.get_all("Print Format",
                           fields=["name", "module", "owner"],
                           limit=20):
    log("  PF:", r.name, "| module:", r.module, "| owner:", r.owner)

log("")
log("=== 3. Workspaces (any) ===")
for r in frappe.db.get_all("Workspace",
                           fields=["name", "label", "owner"],
                           limit=30):
    log("  WS:", r.name, "| label:", r.label, "| owner:", r.owner)

log("")
log("=== 4. Number Cards / Dashboard Charts (any) ===")
for r in frappe.db.get_all("Number Card", fields=["name", "label"], limit=10):
    log("  NC:", r.name, "|", r.label)
for r in frappe.db.get_all("Dashboard Chart", fields=["name"], limit=10):
    log("  DC:", r.name)

log("")
log("=== 5. What each existing fixture file captured (row counts) ===")
import subprocess
out = subprocess.run(
    ["bash", "-c",
     "for f in /home/frappe/frappe-bench/apps/custom_theme/custom_theme/fixtures/*.json; "
     "do python3 -c \"import json,sys; d=json.load(open('$f')); print('$f'.split('/')[-1], len(d))\"; done"],
    capture_output=True, text=True)
if out.returncode == 0:
    log(out.stdout)
else:
    # fallback: read via file API from the app folder
    import os
    base = frappe.get_app_source_path("custom_theme") if hasattr(frappe, "get_app_source_path") else None
    log("(subprocess fallback unavailable:", str(base), ")", out.stderr[:300])

log("")
log("=== 6. Module Def fixtures content ===")
import os
p = "/home/frappe/frappe-bench/apps/custom_theme/custom_theme/fixtures/module_def.json"
if os.path.exists(p):
    data = json.load(open(p))
    log("module_def.json:", [d.get("name") for d in data])
else:
    log("module_def.json not readable from this path")

log("DONE")
