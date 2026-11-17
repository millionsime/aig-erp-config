#!/bin/bash
# Usage: bash run_script.sh /abs/path/to/script.py   (runs against site "frontend")
set -e
SCRIPT="$1"
BASE=$(basename "$SCRIPT")
DEV=~/aig-erpnext-infra/scripts/dev.sh
C=$($DEV ps -q backend 2>/dev/null | head -1)
[ -z "$C" ] && { echo "backend container not running"; exit 1; }
docker cp "$SCRIPT" "$C:/tmp/$BASE"
$DEV exec -T backend bench --site frontend execute custom_theme.aig_runner.run --kwargs "{'path': '/tmp/$BASE'}"
