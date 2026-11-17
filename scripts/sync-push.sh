#!/bin/bash
# usage: scripts/sync-push.sh "what I changed"
set -e
MSG="${1:?describe your change in quotes}"
INFRA="$(cd "$(dirname "$0")/.." && pwd)"
APP=~/custom_theme
DEPLOY=feature/inventory

"$INFRA/scripts/dev.sh" exec -T backend bench --site frontend export-fixtures --app custom_theme
cd "$APP"
BR=$(git branch --show-current)
if [ "$BR" = "$DEPLOY" ]; then
  echo "You are on the deploy branch. First run: git checkout -b feature/<your-topic>"; exit 1
fi
git add -A custom_theme
git diff --cached --quiet && { echo "Nothing changed."; exit 0; }
git diff --cached --stat
read -p "Commit and push these files? [y/N] " a; [ "$a" = y ] || exit 1
git commit -m "$MSG"
git push -u origin "$BR"
echo "Now open a pull request:"
echo "https://github.com/millionsime/aig-erp-theme/compare/$DEPLOY...$BR"