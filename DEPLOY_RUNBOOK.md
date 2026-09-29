# AIG Deployment Runbook — rebuilding the site from git

Everything configured as of 2026-09-29 travels in git now. This is the exact order.

## What lives where

| Repo | Carries |
|---|---|
| `aig-erpnext-infra` | docker compose stack, `apps.json` (pinned frappe v16 / erpnext v16.34.1 / hrms v16.17.1), `.env.example` |
| `custom_theme` | **the carrier app**: 15 fixture sets (40+ custom fields incl. assignment field, 200+ property setters, 576 Custom DocPerms, 30 Server Scripts, Client Scripts, 4 workflows + state/action masters, 17 AIG roles, User Permissions, TWC categories, VAT template, 4 Print Formats, 7 Workspaces, 2 Module Defs) + the 3 custom DocTypes (`aig_custom_theme/doctype/...`) + desk/login CSS/JS + `/aig-admin` dashboard + phase-1 `aig_setup_00–08.py` |
| `aig-erp-config` | 190+ build-out/repair/verify scripts, manuals (`PURCHASE_WALKTHROUGH.md`, `INVENTORY_USER_MANUAL.md`), changelogs, deployment audit — the *source of truth for how*, not needed to rebuild the *state* |

## Rebuild steps (target server)

1. **Stack**: clone `aig-erpnext-infra`, `cp .env.example .env` (edit passwords; **add `server_script_enabled=1`** — without it all 30 Server Scripts silently do nothing), `docker compose up -d`, create site `frontend`.
2. **App**: inside backend container `bench get-app https://github.com/millionsime/aig-erp-theme custom_theme && bench --site frontend install-app custom_theme`.
3. **Sync config**: `bench --site frontend migrate` — fixtures re-apply every time (idempotent). Custom DocTypes come from the app JSON.
4. **Company data**: create Company `Adama Investment Group` (abbr `AIG`), Chart of Accounts import + fiscal year + users either by restoring the site backup (fastest, carries everything incl. demo data) or running the phase-1 setup scripts `aig_setup_00–08.py` in order.
5. **Global Defaults (desk charts!)**: right after the company exists run script `179_global_defaults.py` — without it every desk dashboard chart (Selling/Buying dashboards) shows **"Company is mandatory"**. It sets default company + currency and clears cache. (Deliberately NOT a fixture: the company must exist first, or migrate would fail on a dangling link.)
6. **Demo data (optional)**: `bench --site frontend execute` the seeder `170_accounting_demo_seed.py` — aborts if markers exist.
7. **Verify**: run `161_post_migrate_sanity.py` (counts + 4 guards) and `176_enduser_route_verify.py` (10/10). Open `/aig-admin`.
6. **Demo data (optional)**: `bench --site frontend execute` the seeder `170_accounting_demo_seed.py` — aborts if markers exist.
7. **Verify**: run `161_post_migrate_sanity.py` (counts + 4 guards) and `176_enduser_route_verify.py` (10/10). Open `/aig-admin`.

## What does NOT travel in git
Users & passwords, naming counters, demo transactions (MR/PO/PR/PI/PE/SI/JE/SR/Budgets), site config (`server_script_enabled`, hosts) — all covered by step 1 config + step 4 backup/seed.
