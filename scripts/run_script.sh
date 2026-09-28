#!/bin/bash
# Robust runner: executes an AIG setup script against site 'frontend' via
# `bench execute` (proper Frappe bootstrap) using the custom_theme.aig_runner
# helper, which runs the file in one consistent namespace and commits.
# Usage: bash run_script.sh /abs/path/to/script.py
set -e
SCRIPT="$1"
C=frappe_docker-backend-1
APP=/home/frappe/frappe-bench/apps/custom_theme/custom_theme
BASE=$(basename "$SCRIPT")
docker cp ~/aig-erp-config/scripts/aig_runner.py $C:$APP/aig_runner.py
docker cp "$SCRIPT" $C:/tmp/$BASE
docker exec -w /home/frappe/frappe-bench $C \
  bench --site frontend execute custom_theme.aig_runner.run --kwargs "{'path': '/tmp/$BASE'}"
