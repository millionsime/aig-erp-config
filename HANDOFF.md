# AIG ERP — handoff (state as of 2026-11-20)

Read this first if you are picking up the work in a new chat. It replaces the
chat history: what exists, what was decided, what is half-done, what is next.

## 1. The system

| Piece | Where |
|---|---|
| Server | `aig-fms`, Ubuntu 22.04, user `aigadmin`, public 196.190.216.38, LAN 172.25.14.46 |
| Live site | https://aigerp.duckdns.org (site name `aigerp.duckdns.org`), Traefik + Let's Encrypt |
| Stack | Frappe 16.56.0, ERPNext 16.55.0, HRMS 16.53.2, `custom_theme`, `aig_ethiopian_calendar` |
| Image | built by GitHub Actions in `aig-erpnext-infra`, pushed to `ghcr.io/millionsime/aig-erpnext:<sha>` |
| Backups | `~/scripts/backup.sh` on the server, cron 02:00, rclone to Google Drive `gdrive:aig-erpnext-backups`; restore proven on a test site |
| Dev laptop | `yai70`, WSL2. Local stack: `~/aig-erpnext-infra/scripts/dev.sh <compose args>` (site `frontend`, http://localhost:8080) |

### Repositories (all `github.com/millionsime/...`)

| Repo | Local path | Role |
|---|---|---|
| `aig-erpnext-infra` | `~/aig-erpnext-infra` | compose files, `apps.json`, deploy workflow, `scripts/dev.sh`, sync scripts. Push to `main` = build + deploy to the server. |
| `aig-erp-theme` | `~/custom_theme` | the custom Frappe app `custom_theme` (module `aig_custom_theme`): ALL configuration as fixtures + code. Server builds it from branch **`feature/inventory`**. |
| `aig-ethiopian-calendar` | `~/aig-ethiopian-calendar` | calendar app, branch `main`. Owns its own Module Def. |
| `aig-erp-config` | `~/aig-erp-config` | one-time setup scripts (company, chart of accounts, tax wiring), run with `bash scripts/run_script.sh scripts/<file>.py` |

Theme branch `main` is OLD (17 commits behind `feature/inventory`) — do not deploy from it.

## 2. Rules we agreed (also in the theme repo's CONTRIBUTING.md)

1. Every configuration change lives in `custom_theme` as a file. Only business data lives only in the database.
2. ERPNext / Frappe / HRMS core code is never edited. Versions are pinned in `apps.json`.
3. No configuration changes directly on the server. Make them locally, export, PR, merge, deploy.
4. Work on `feature/<topic>` branches; merge only by pull request. AI agents too (an agent's unreviewed commit nearly re-pointed the server at the stale theme `main`).
5. Chart of accounts, company, cost centers are NOT fixtures: they are `aig-erp-config` scripts run once per site.

### Fixture capture (theme `hooks.py`)
- Custom Field and Property Setter: `is_system_generated = 0` (anything made in the UI). Property Setter also keeps 213 shipped settings-driven rows by name, listed in `custom_theme/fixture_lists.py` — do not add to that list.
- Print Format (`standard=No`), Report (`is_standard=No`), Notification (`is_standard=0`), Server/Client Script, Workflow State → Workflow Action Master → Workflow (order matters), Role `AIG%`, Custom DocPerm for AIG roles, Module Def `AIG%` except the calendar's, Workspace `AIG%`, Leave Type (3).
- Fixtures add/update but never delete. Removing something everywhere needs a patch in `custom_theme/patches/`.

### Daily loop (after infra PR #1 is merged)
```bash
~/aig-erpnext-infra/scripts/sync-pull.sh               # get merged work, migrate local site
~/aig-erpnext-infra/scripts/sync-push.sh "what I did"  # export fixtures, commit on feature branch, push, prints PR link
```

## 3. Open pull requests — merge in this order

1. Back up the server: `~/scripts/backup.sh`.
2. Add repo secret `INFRA_DISPATCH_TOKEN` in `aig-erp-theme` (fine-grained token on `aig-erpnext-infra`, Actions: read+write).
3. **infra PR #1** https://github.com/millionsime/aig-erpnext-infra/pull/1 — pins versions, `workflow_dispatch` on deploy.yml, removes misplaced trigger, adds sync scripts, `bench backup` before every migrate. Merging deploys the current theme on the pinned versions (no functional change).
4. **theme PR #2** https://github.com/millionsime/aig-erp-theme/pull/2 (`feature/fixtures-refresh` → `feature/inventory`) — capture-everything fixture filters, re-exported fixtures incl. test field `Customer-custom_test_data` ("TEST DATA"), Tax Withholding Category naming fix, calendar Module Def fix, deploy trigger workflow, CONTRIBUTING.md. Merging should auto-trigger the deploy.

End-to-end test: after step 4, Customer form on the server shows **TEST DATA**. Then delete the field locally and remove it everywhere with a patch.

Housekeeping on the laptop: infra `main` had an unpushed Codebuff commit `2590ea6`; plan was `git branch codebuff/pin-versions 2590ea6 && git reset --hard origin/main`. Laptop branch `theme-only` (theme reduced to "presentation only") was never pushed and is abandoned; tag `backup/theme-only-2026-11-17` may exist.

## 4. Chart of accounts (done on the LOCAL site only)

- Source: `AIG_Final_Chart_of_Accounts_4.csv` (219 rows). Additions over the finance file: 50108 Stock Adjustment, 50109 Expenses Included In Valuation, 21607 Stock Received But Not Billed, 21608 Asset Received But Not Billed.
- Local site imported it (Company "Adama Investment Group", abbr AIG, ETB). Before import, default-account links had to be cleared: Expense Claim Account rows, Ethiopia Tax templates, Mode of Payment Account rows.
- Company defaults: bank 11012, cash 10001, receivable 12300, payable 21100, inventory 13103, stock adjustment 50108, default expense 50101, round off "Round Off - AIG"; tax templates → 21402 VAT 15%; withholding: 7.5% → 21401, 3% → 21403 (via `custom_theme.aig_custom_theme.setup.ensure_tax_setup.run`).
- Warehouse→account intended mapping: WIP 13102, Finished Goods 13103, Stores 13104, Goods In Transit 13101 (placeholder), All Warehouses 13104.

**In git (branch `feature/coa-219`)** — the order to rebuild the chart on any site:
```bash
cd ~/aig-erp-config
bash scripts/run_script.sh scripts/190_coa_unlink_default_accounts.py   # must end "remaining links: 0"
bash scripts/run_script.sh scripts/83_import_coa.py                      # imports AIG_Corrected_Demo_CoA.csv (219 rows)
bash scripts/run_script.sh scripts/84_wire_new_coa.py
bash scripts/run_script.sh scripts/86_repair_post_import.py
bash scripts/run_script.sh scripts/191_coa_stock_defaults.py
bash scripts/run_script.sh scripts/192_coa_warehouse_accounts.py
bash scripts/run_script.sh scripts/194_company_foundation.py           # fiscal years, cost centers (from aig_hr), company CC
bash scripts/run_script.sh scripts/195_org_structure.py                 # needs aig_hr installed: 52 units + their cost centers
~/aig-erpnext-infra/scripts/dev.sh exec -T backend bench --site frontend execute custom_theme.aig_custom_theme.setup.ensure_tax_setup.run
bash scripts/run_script.sh scripts/85_coa_health.py
bash scripts/run_script.sh scripts/193_core_untouched.py                 # expect 0
```
`run_script.sh` now finds the container through `dev.sh` and copies the CSV in for you.

**Server:** CoA not touched. Before running any CoA script there: backup, and confirm GL Entry count is 0.

## 5. Next work, in order

1. Merge the two PRs (section 3) and confirm TEST DATA appears on the server.
2. Merge `aig-erp-config` PR `feature/coa-219` (CoA scripts 190–193 + 219-row CSV).
3. Install the aig_hr app (fork at millionsime/aig_hr), then run 194 + 195. Source of truth for org units and cost centers: aig_hr/data/*.json.
4. Decide `Expense Claims - AIG` (HRMS re-creates it unnumbered under 60900) — keep, or add a proper payable account and repoint Expense Claim Types.
5. Capture Selling/Buying/Stock/Accounts Settings (singles) — careful, some hold company-specific links.
6. Run the core-untouched check on laptop and server (`docker diff` on backend for `apps/frappe|erpnext|hrms`).
7. Then CoA + cost centers on the server, real data restore, rotate exposed secrets (admin password, DB root, deploy key, PAT).

## 6. Known quirks
- `bench execute` via `aig_runner` prints a trailing `NameError: name 'custom_theme' is not defined` — harmless.
- Script 86 "VERDICT !!" is a stale count expectation (it expects 177 accounts; 218–222 is correct now).
- Server Scripts need `server_script_enabled` (set globally with `bench set-config -g`).
