# AIG Deployment Runbook — rebuilding the site from git

Everything configured as of 2026-11-16 travels in git. This is the exact order.

## What lives where

| Repo | Carries |
|---|---|
| `aig-erpnext-infra` | docker compose stack, `apps.json` (pinned: `frappe` / `erpnext` / `hrms` on `version-16`, `aig-erp-theme` on **`feature/inventory`**, `aig-ethiopian-calendar` on `main`), `.env.example` |
| `custom_theme` | **the carrier app**: the fixture set declared in `hooks.py` (13 JSON files — `aig*` Custom Fields, Property Setters, Custom DocPerms filtered to the AIG roles, Server Scripts, Client Scripts, Workflows + state/action masters, AIG Roles, Leave Types, Module Defs, Print Formats, Workspaces) + the 3 custom DocTypes (`aig_custom_theme/doctype/...`) + desk/login CSS/JS + `/aig-admin` dashboard + phase-1 `aig_setup_00–08.py` |
| `aig-erp-config` | 190+ build-out/repair/verify scripts, manuals (`PURCHASE_WALKTHROUGH.md`, `INVENTORY_USER_MANUAL.md`), changelogs, deployment audit — the *source of truth for how*, not needed to rebuild the *state* |

Two things deliberately do **not** ship with the app:

- **No seed data and no `after_install` hook.** The seed layer (`setup/seed.py`,
  `setup/inventory_seed.py`, `setup/data/*`, the `aig_0001`/`aig_0002` migrate
  patches) was removed in `custom_theme` commit `049e642`. `bench migrate` creates
  no company, cost centers, warehouses, settings single or inventory masters.
- **No User Permission fixtures.** Per-user scoping is site data and is applied on
  the site itself (scripts `32_inv_roles_users.py`, `183_self_service_demo_setup.py`),
  never carried in git.

## Rebuild steps (target server)

1. **Stack**: clone `aig-erpnext-infra`, `cp .env.example .env` (edit passwords;
   **add `server_script_enabled=1`** — without it all AIG Server Scripts silently
   do nothing), `docker compose up -d`, create site `frontend`. The apps are
   installed at the branches `apps.json` pins, so `custom_theme` arrives on
   `feature/inventory`.
2. **App**: inside the backend container
   `bench get-app https://github.com/millionsime/aig-erp-theme --branch feature/inventory custom_theme`
   (first time only) then `bench --site frontend install-app custom_theme`.
3. **Sync config**: `bench --site frontend migrate` — the 13 fixture files re-apply
   every time (idempotent) and the custom DocTypes come from the app JSON. Nothing
   else is created: there is no `after_install` seed and no seed patch any more.
4. **Company and master data** — the app no longer seeds any of this. Either:
   - **restore the site backup** (fastest; carries company, masters, users and demo
     data), or
   - create Company `Adama Investment Group` (abbr `AIG`), then run the phase-1
     scripts `custom_theme/aig_setup_00–08.py` in order (`bench --site frontend
     execute custom_theme.aig_setup_00.run`, …), and optionally
     `scripts/56_build_c_cost_centers.py` to standardise the cost-center tree.
   Warehouses are plain site records: each store needs `Warehouse.aig_cost_center`
   set (that field **is** the isolation key — a store with an enterprise is
   `isolated`, a store without one is `mixed`).
5. **User Permissions**: apply the per-user Cost Center / Warehouse scoping on the
   site (scripts `32_inv_roles_users.py`, `183_self_service_demo_setup.py`, or a
   `user,enterprise` CSV). These rows never travel in git.
6. **Global Defaults (desk charts!)**: right after the company exists run script
   `179_global_defaults.py` — without it every desk dashboard chart
   (Selling/Buying dashboards) shows **"Company is mandatory"**. It sets default
   company + currency and clears cache. (Deliberately NOT a fixture: the company
   must exist first, or migrate would fail on a dangling link.)
7. **Tax configuration**: the AIG tax templates and withholding categories are not
   fixtures (they hardwire CoA-2.0 account names 21402/21401/21403). After the CoA
   importer chain has run:
   `bench --site frontend execute custom_theme.aig_custom_theme.setup.ensure_tax_setup.run`
   — idempotent, a safe no-op on a site still on the standard CoA.
8. **Chart of Accounts (if not restoring a backup)**: a fresh site gets ERPNext's
   standard CoA. To adopt the AIG corrected v2 CoA run the importer chain
   `80` purge → `81` preflight → `83` import → `84`/`86` wiring → `85` health
   **before go-live postings**.
9. **Demo data (optional)**: `bench --site frontend execute` the seeder
   `170_accounting_demo_seed.py` — aborts if markers exist.
10. **Verify**: run `161_post_migrate_sanity.py` (counts + 4 guards) and
    `176_enduser_route_verify.py` (10/10). Open `/aig-admin`.

## What does NOT travel in git

Users & passwords, User Permissions, naming counters, demo transactions
(MR/PO/PR/PI/PE/SI/JE/SR/Budgets), company / cost center / warehouse / inventory
masters (no seed layer any more), site config (`server_script_enabled`, hosts) —
all covered by step 1 config plus the step 4 backup or scripts.
