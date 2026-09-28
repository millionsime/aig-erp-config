# aig-erp-config

Build-out scripts and manuals for the **AIG ERPNext v16** site `frontend`
(company: Adama Investment Group). This repo IS the configuration: every
phase of AIG customization was applied by the numbered scripts here, and the
site's fixtures are exported into the `custom_theme` app
(https://github.com/millionsime/aig-erp-theme).

## Layout

- `scripts/` — numbered build/verify scripts, run in order (131 → 157b are
  the phase-3 procurement/payment refinement). `run_script.sh` + `aig_runner.py`
  execute them inside the backend container via
  `bench --site frontend execute custom_theme.aig_runner.run`; the runner
  **commits only on success** (any crash = full rollback; the trailing
  `NameError: name 'custom_theme' is not defined` is a cosmetic bench artifact).
- `PROCUREMENT_REFINE_CHANGELOG.md` — what each phase changed and why.
- `PURCHASE_WALKTHROUGH.md` — live demo walkthrough (logins, clicks, wow moments).
- `DEPLOYMENT_AUDIT.md` — fixtures/DB/git inventory and time bombs.
- `INVENTORY_USER_MANUAL.md`, older `.txt` reports — earlier phases.

## Deployment order on a fresh server

1. Deploy `aig-erpnext-infra` (docker compose) with pinned versions
   (`apps.json` tags + `.env` per `.env.example`).
2. `bench --site <site> set-config server_script_enabled 1` (**required** —
   all 29 AIG Server Scripts are inert without it).
3. Install `custom_theme` from GitHub → `bench migrate` (fixtures apply).
4. Run the setup scripts in order (they are idempotent): phase-1
   `custom_theme/aig_setup_00–08.py`, then `scripts/131` → `157b`.
5. Restore demo data via site backup if wanted (demo data is NOT in git).

See `DEPLOYMENT_AUDIT.md` for the full reasoning and the audit scripts
(`154`/`155`) that produced it.
