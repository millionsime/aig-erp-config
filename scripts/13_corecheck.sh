#!/bin/bash
# Confirm no core frappe/erpnext source files were modified.
C=frappe_docker-backend-1
echo "===== git status: apps/frappe ====="
docker exec -w /home/frappe/frappe-bench/apps/frappe $C git status --porcelain 2>&1 | head -20
echo "(exit: $?)"
echo "===== git status: apps/erpnext ====="
docker exec -w /home/frappe/frappe-bench/apps/erpnext $C git status --porcelain 2>&1 | head -20
echo "(exit: $?)"
echo "===== core .py/.js/.json modified in last 3 days (should be empty) ====="
docker exec $C bash -c "find apps/frappe apps/erpnext -type f \( -name '*.py' -o -name '*.js' -o -name '*.json' \) -mtime -3 2>/dev/null | head -40"
echo "===== files added under apps/custom_theme (custom app - allowed) ====="
docker exec -w /home/frappe/frappe-bench/apps/custom_theme $C git status --porcelain 2>&1 | head -40
