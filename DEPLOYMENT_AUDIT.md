# AIG Deployment Audit — what exists where, and what can move to the deployment server

**Date:** 2026-09-28 · **Site:** `frontend` (frappe 16.33.0, erpnext 16.34.1, hrms 16.17.1 — all UNVERSIONED; custom_theme 0.0.1 @ main)
**UPDATE (same day, P0–P2 done):** fixtures ARE now exported (see §3b), `aig-erp-config` is git-committed, apps.json is pinned by tag, and time bombs 1/4/5 are DEFUSED (156/157b). Status notes inline.

## 1. Fixtures: **zero**

`custom_theme/hooks.py` declares **no `fixtures`** and no `doc_events`. Nothing in the site configuration is exported to the app repo. Everything below lives **only in the site database** and would be lost on a fresh `bench` install (apps alone give you a vanilla ERPNext with a logo):

| Configuration in the DB | Count |
|---|---|
| Custom DocPerm (the AIG-only permission sets) | **576** |
| Property Setter | 203 |
| Custom Field | 89 |
| Server Script (all the guards/gates/withholder) | **29** |
| Client Script | 11 |
| Workflow (Stock Request, Procurement, Payment, Store Receiving) | 4 |
| Role (AIG roles) | 17 |
| User Permission (enterprise scoping) | 47 |
| Custom DocTypes (AIG Committee Signoff; 2× Stock Migration) | 3 |
| Accounts / Cost Centers / WH categories / company defaults | 177 / 19 / 2 / several |

**Demo/transaction data is small:** 8 MRs (4 Draft, 1 Pending Store Review, 3 Approved), 3 POs (2 Pending Committee Signoff, 1 Pending Finance Signoff), 0 PR/PI/PE, 11 items, 4 suppliers, 23 users, naming counters (MAT-MR→15, PUR-ORD→18, ACC-PAY→11, …).

## 2. What GitHub currently carries (and what it doesn't)

| Repo (WSL path) | Remote | Contents | Phase-3 config? |
|---|---|---|---|
| `~/aig-erpnext-infra` | millionsime/aig-erpnext-infra | compose.yaml, apps.json, overrides, scripts (the deployment itself) | ❌ |
| `~/custom_theme` | millionsime/aig-erp-theme | theme/login assets, logo, `aig_setup_00–08.py` (phase-1), **`aig_runner.py` is NOT tracked** | ❌ |
| `~/custom_app` | millionsime/aig-erp-custom-app | `aig_hr` app skeleton (**not installed** — infra commit "Temporarly remove custom app") | ❌ |
| `~/aig-erp-config` | **NOT a git repo at all** | **165 scripts (131–155: every phase-2/3 change)** + run_script.sh + aig_runner.py + all manuals/changelogs | ❌ everything |

**Answer:** as of today, GitHub **cannot** rebuild this site. The purchase workflows, committee rules, withholder, permissions — the entire phase-2/3 refinement — exists nowhere but the site DB and the un-versioned `aig-erp-config` folder. GitHub also cannot carry the demo *data*; that travels in a database backup or a seeder script.

## 3. Two ways to move everything

**A. Full site backup (fast, includes demo data, users, counters)**
```bash
docker exec frappe_docker-backend-1 bench --site frontend backup --with-files
# restore on target: bench --site <new> restore <sql.gz> --with-files
```
Moves 100% (config + demo data + counters). Best for "I want the demo server identical, now". Risk: also carries hidden cruft; passwords/secrets inside.

**B. Fixtures + config repo (clean, reproducible, the right long-term move) — DONE 2026-09-28**
1. ✔ `git init` + commit `~/aig-erp-config` (192 files; push when ready: remote not yet added).
2. ✔ `fixtures = [...]` added to `custom_theme/hooks.py`; `bench export-fixtures` committed in the theme repo (11 JSON files, 529 KB: Custom Field filtered to `aig%` = 41 AIG fields, Property Setter/Custom DocPerm/Server Script/Client Script/Workflow/Role/User Permission/WH categories/tax template/Module Defs). Custom DocTypes + `model_42_handover_document` stay script-owned (developer-mode export refused).
3. ✔ On-target flow proven live: `bench migrate` re-synced all fixtures; counts stable (29 scripts / 4 workflows / 89 fields / 576 docperms) and all guards still live (161).
Demo data still needs the backup restore **or** a demo-seeder script.

## 4. Time bombs to defuse before deploying

1. **`server_script_enabled = 1` (common_site_config).** All 29 Server Scripts are inert without it — on a fresh server the raw-submit guards, committee majority, Model 42, Three-Way Match and **the payment withholder** all silently disappear. Must be set in the target's common_site_config *before* go-live (infra repo change + redeploy). *(Documented in infra `.env.example`; not yet applied to any target.)*
2. **`aig_runner.py` must not survive to production.** It executes arbitrary `/tmp/*.py` as Administrator with a trailing commit, via docker-cp. Keep it out of the image / delete it after setup; use `bench --site frontend execute` for auditable paths instead.
3. **hrms/frappe/erpnext are UNVERSIONED** in the bench. Pin exact versions in `aig-erpnext-infra/apps.json` so the deployment server builds the same stack (16.33.0 / 16.34.1 / 16.17.1 today).
4. ✔ DEFUSED (156): **withholder now throws** if a referenced PI's supplier carries a Tax Withholding Category ("AIG double-withholding guard: …"). Verified live with a probe supplier.
5. ✔ DEFUSED (157b): **MR CC Normalize now throws loudly** when the header is root/HO/empty and no row warehouse provides an `aig_cost_center`, naming the warehouses. Note (158 probe): "AIG - MR Request Defaults" (Before Insert) pre-empts empty headers via user-permission fallback, so the guard is the safety net for the root/empty-header path; a bad warehouse on a fresh doc gets the officer's enterprise CC (plausible-but-wrong, still buttons-alive) — consider a client-side warning later.
6. **Module "AIG HR" exists in the DB but its app is not installed.** The AIG Committee Signoff DocType points at it. The fixtures route now exports the Module Def (module_def.json), but DocType fixtures cannot be exported outside developer mode — the script chain (132) recreates the DocType; keep that order (migrate → scripts).
7. **Naming-series counters only travel with a DB copy.** A fixture-based rebuild starts counters at 0; mixing strategies (fresh site + imported old docs) can collide. Keep one strategy per environment.
8. **Scheduler must run on the target** (it does here). Nothing critical depends on it today, but workflow notifications and log clearing do.
9. **Push the three repos** (remotes exist for custom_theme/custom_app/infra; `aig-erp-config` has no remote yet): `git -C ~/aig-erp-config remote add origin <url> && git push`, then push custom_theme + infra. Uncommitted `deploy.yml` change in infra is NOT from the audit — review separately.

*Audit scripts: `154_deployment_audit.py`, `155_deployment_audit2.py` (both read-only).*
