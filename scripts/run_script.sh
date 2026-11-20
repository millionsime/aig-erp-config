#!/bin/bash
# Run an AIG setup script against the local site 'frontend'.
# Usage (from ~/aig-erp-config):  bash scripts/run_script.sh scripts/<file>.py
# Works with the dev stack from aig-erpnext-infra (scripts/dev.sh), whatever the
# container is called. Also copies the chart CSV into the container so
# 83_import_coa.py finds it at /tmp/AIG_Corrected_Demo_CoA.csv.
set -e
SCRIPT="$1"
[ -f "$SCRIPT" ] || { echo "usage: bash scripts/run_script.sh scripts/<file>.py"; exit 1; }
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DEV="${AIG_DEV:-$HOME/aig-erpnext-infra/scripts/dev.sh}"
BASE=$(basename "$SCRIPT")
C=$($DEV ps -q backend 2>/dev/null | head -1)
[ -z "$C" ] && { echo "backend container not running (start it with: $DEV up -d)"; exit 1; }
APP=/home/frappe/frappe-bench/apps/custom_theme/custom_theme
docker cp "$HERE/scripts/aig_runner.py" "$C:$APP/aig_runner.py"
docker cp "$HERE/AIG_Corrected_Demo_CoA.csv" "$C:/tmp/AIG_Corrected_Demo_CoA.csv"
docker cp "$SCRIPT" "$C:/tmp/$BASE"
$DEV exec -T backend bench --site frontend execute custom_theme.aig_runner.run \
  --kwargs "{'path': '/tmp/$BASE'}" 2>&1 | grep -v "name 'custom_theme' is not defined" || true
