#!/bin/bash
set -e
INFRA="$(cd "$(dirname "$0")/.." && pwd)"
DEV="$INFRA/scripts/dev.sh"
DEPLOY=feature/inventory

git -C "$INFRA" pull --ff-only
git -C ~/aig-erp-config pull --ff-only
git -C ~/aig-ethiopian-calendar pull --ff-only
git -C ~/custom_theme pull origin "$DEPLOY"     

$DEV pull -q
$DEV up -d
$DEV exec -T backend bench --site frontend migrate
$DEV exec -T backend bench --site frontend clear-cache
echo "In sync."