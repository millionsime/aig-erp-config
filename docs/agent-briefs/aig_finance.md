# Build brief: `aig_finance` — AIG Finance configuration app

Paste this whole file to the coding agent as its task. Work in small steps
and stop at each **CHECKPOINT** for review.

---

## 0. Non-negotiable rules (read first)

1. **Never touch ERPNext / Frappe / HRMS core.** Do not edit, copy over or
   reformat any file under `apps/frappe`, `apps/erpnext`, `apps/hrms`. Do not
   change standard DocTypes in the database. Do not monkey-patch core code.
   Extend only through documented hooks. Upgrades of ERPNext must never
   conflict with this app.
2. **Everything is a file in this app.** No Server Script / Client Script
   records, no "configure it in the UI and forget". The app's data files are
   the source of truth; the site is made to match them.
3. **Git:** work on `feature/<topic>` branches in `millionsime/aig-finance`,
   Conventional Commits, `git status` + `git diff --stat` before every commit,
   never `git add .`, never force-push, never commit secrets or dumps.
4. **Sites:** work only on the local dev site `frontend`. Never touch the
   production server. Never run destructive commands (drop-site, reinstall,
   uninstall-app, deleting records, `git reset --hard`) without an explicit
   yes from the user in the conversation.
5. **Stay in scope.** Only the areas listed in section 3. If a task needs a
   change in `custom_theme`, `aig_hr`, the calendar app or infra, report it
   and stop.
6. Create `knowledge.md` (agent rules, copy from `aig-erp-config/knowledge.md`)
   at the repo root as the first commit.

## 1. Context

- Stack: Frappe 16.56.0, ERPNext 16.55.0, HRMS 16.53.2 (pinned in
  `aig-erpnext-infra/apps.json`). Docker dev stack via
  `~/aig-erpnext-infra/scripts/dev.sh`; site `frontend`.
- Company: **Adama Investment Group**, abbreviation **AIG**, currency **ETB**,
  country Ethiopia.
- Chart of accounts: 219 numbered accounts, imported by
  `aig-erp-config` (`AIG_Corrected_Demo_CoA.csv`). Account names on the site
  are `"<number> - <name> - AIG"`.
- Cost centers and org units come from the `aig_hr` app
  (`aig_hr/data/*.json`); default cost center `1.1 - Head Office - General - AIG`.
- Every value this app sets is a **management decision** recorded in the
  doc "AIG Finance Default Accounts: Decisions for Management", referenced as
  `D-01`…`D-31` and `P-1`…`P-9`. Until management signs, those entries are
  `pending_decision` and are not applied.

## 2. Naming and conventions

| Thing | Name |
| --- | --- |
| GitHub repo | `millionsime/aig-finance` |
| Python package / app name | `aig_finance` |
| App title | `AIG Finance` |
| Module (modules.txt, Module Def) | `AIG Finance` |
| Publisher | `AIG Tech Enterprise` |
| Licence | MIT |
| Custom Field fieldnames (if ever needed) | prefix `aig_fin_` |
| New DocTypes (only if truly needed) | prefix `AIG Finance ` (e.g. `AIG Finance Setup Log`) |
| Patches | `aig_finance.patches.v1_0.<verb>_<object>` |
| Data files | `aig_finance/data/<snake_case>.json` |
| Functions | `snake_case` verbs: `apply_company_defaults`, `validate_data` |
| Constants | `UPPER_SNAKE_CASE` |
| Branches | `feature/<topic>`, `fix/<topic>` |
| Commits | `feat(finance): add company defaults applier` |

Python: type hints on public functions, docstrings, no wildcard imports,
format with the repo's pre-commit (ruff). Tabs for indentation, as Frappe apps do.

## 3. Scope — what this app owns

| Area | Records | Decision refs |
| --- | --- | --- |
| Chart additions | the 12 new accounts in section 11 of the decision paper | D-03…D-31 |
| Company accounting defaults | the Company fields in section 5 below | D-01…D-31 |
| Fiscal years | EFY Hamle 1 – Sene 30 | P-1 |
| Accounting periods / month lock | monthly Accounting Periods, frozen-entries role | P-3 |
| Modes of Payment | default account per company | D-16, D-17 |
| Banks and Bank Accounts | one Bank Account record per GL bank account (11001–11021) | D-15 |
| Payment Terms | supplier / customer templates | P-5 |
| Accounts Settings | only the settings tied to the policies above | P-3, P-7 |

**Not this app** (leave alone, note in README): tax templates, tax rules,
withholding categories (`aig_tax`); warehouses, warehouse accounts, item
defaults (`aig_stock`); asset categories, finance books (`aig_assets`);
salary structures and payroll (`aig_hr`). Company fields that belong to those
apps are listed in `OWNERSHIP` and never written here.

## 4. Architecture (declarative data + idempotent appliers)

```
aig-finance/
├── README.md               what it does, how to run, ownership table
├── CHANGELOG.md
├── knowledge.md            agent rules
├── license.txt
├── pyproject.toml
└── aig_finance/
    ├── __init__.py         __version__ = "0.1.0"
    ├── hooks.py
    ├── modules.txt         AIG Finance
    ├── patches.txt
    ├── data/               SOURCE OF TRUTH (reviewed by finance)
    │   ├── chart_additions.json
    │   ├── company_defaults.json
    │   ├── fiscal_years.json
    │   ├── accounting_periods.json
    │   ├── modes_of_payment.json
    │   ├── bank_accounts.json
    │   └── payment_terms.json
    ├── setup/
    │   ├── __init__.py
    │   ├── apply.py        orchestrator: run(dry_run=True, only=None)
    │   ├── context.py      company, abbr, account lookup by number
    │   ├── validation.py   schema + reference checks, no DB writes
    │   ├── report.py       structured result: created / updated / unchanged / skipped / errors
    │   ├── chart.py
    │   ├── company.py
    │   ├── fiscal.py
    │   ├── payments.py
    │   └── banking.py
    ├── patches/v1_0/__init__.py
    ├── aig_finance/        module folder (empty unless a DocType is added)
    └── tests/
        ├── test_validation.py
        └── test_apply.py
```

Rules for the appliers:

1. **Reference accounts by number, never by name.** `context.account("21402")`
   resolves `21402 - VAT Payable 15% - AIG` for the company; missing account =
   an error in the report, not a crash.
2. **Each data entry carries** `"ref"` (e.g. `"D-11"`) and `"status"`:
   `"approved"` or `"pending_decision"`. Pending entries are skipped and
   listed in the report.
3. **Idempotent desired state.** Running twice changes nothing the second time.
   A value on the site that differs from the data file is reported as
   `drift` with old and new values, then set to the file's value.
4. **Never delete** anything. Removing a record needs its own reviewed patch.
5. **Dry run is the default.** `run(dry_run=True)` validates, computes every
   change and prints the report without writing. `dry_run=False` writes in one
   transaction and rolls back on any error.
6. **Prerequisites:** if the company or the chart (account 21402) is missing,
   return a report saying so and write nothing — never raise during migrate.
7. **Respect OWNERSHIP:** `company.py` has an explicit allow-list of the
   fields it may write; anything else is refused at validation time.

Wiring in `hooks.py`:

```python
required_apps = ["erpnext", "hrms"]
after_migrate = ["aig_finance.setup.apply.run_after_migrate"]   # applies approved entries, logs report, never raises
```

Manual use:

```bash
bench --site frontend execute aig_finance.setup.apply.run                        # dry run
bench --site frontend execute aig_finance.setup.apply.run --kwargs "{'dry_run': 0}"
bench --site frontend execute aig_finance.setup.apply.run --kwargs "{'only': 'company'}"
```

## 5. Company fields owned by this app

Check every fieldname against `frappe.get_meta("Company")` on the installed
version before using it; if a field does not exist, report it, do not guess.

| Company field | Ref | Recommended value (account number) |
| --- | --- | --- |
| default_receivable_account | D-01 | 12300 |
| default_payable_account | D-02 | 21100 |
| default_income_account | D-03 | 40409 (new) |
| default_expense_account | D-04 | 60416 (new) — replaces 50101 |
| default_advance_received_account | D-05 | 21410 (new) |
| default_advance_paid_account | D-06 | 12105 |
| default_deferred_revenue_account | D-07 | 21409 |
| default_deferred_expense_account | D-08 | 12109 (new) |
| default_discount_account | D-09 | none unless management picks 40404 |
| default_bank_account | D-15 | 11012 |
| default_cash_account | D-16 | 11501 |
| default_payroll_payable_account | D-25 | 21601 |
| default_employee_advance_account | D-26 | 12600 |
| default_expense_claim_payable_account | D-27 | 21300 |
| exchange_gain_loss_account | D-28 | 40406 (new) |
| unrealized_exchange_gain_loss_account | D-29 | 40407 (new) |
| round_off_account | D-30 | 60414 (new) |
| round_off_cost_center | P-6 | 1.1 - Head Office - General |
| write_off_account | D-31 | 60415 (new) |
| cost_center | P-6 | 1.1 - Head Office - General |

**Not owned here:** stock fields (D-18…D-21 → `aig_stock`), asset fields
(D-22…D-24, depreciation accounts → `aig_assets`).

Initial status of every entry: `pending_decision`, except D-01, D-02, D-15
and P-6, which are already in use and can start as `approved`.

## 6. Data file shape (example)

```json
{
  "schema_version": 1,
  "company": "Adama Investment Group",
  "decision_document": "AIG Finance Default Accounts: Decisions for Management",
  "entries": [
    {"field": "default_expense_account", "account_number": "60416",
     "ref": "D-04", "status": "pending_decision",
     "note": "Review account; finance clears to zero monthly"}
  ]
}
```

`chart_additions.json` entries: `account_number`, `account_name`,
`parent_account_number`, `root_type`, `account_type`, `is_group`, `ref`,
`status`. Created under the parent found by number; currency ETB.

`fiscal_years.json`: EFY 2018 = 2025-07-08 → 2026-07-07, EFY 2019 =
2026-07-08 → 2027-07-07, named `2025-2026 (EFY 2018)` etc. If a fiscal year
already covers the dates, report it and leave it.

## 7. Relationship to existing scripts

`aig-erp-config` scripts `84`, `86`, `191` and the fiscal-year part of `194`
set some of the same Company fields. Do not edit or delete them. In this
app's README, add a "Supersedes" section listing them, and propose (do not
make) a follow-up PR in `aig-erp-config` that marks them deprecated.

Known issue to report, not fix: `custom_theme/aig_custom_theme/setup/ensure_tax_setup.py`
posts purchase VAT to 21402; decision D-11 says 12201. That belongs to `aig_tax`.

## 8. Work plan and checkpoints

1. Scaffold with `bench new-app aig_finance` inside the dev container
   (title, publisher, licence from section 2), move it to `~/aig-finance`, add
   `knowledge.md`, README, CHANGELOG. Push branch `feature/scaffold`.
   **CHECKPOINT 1** — show the tree and `hooks.py`.
2. `context.py`, `validation.py`, `report.py`, `apply.py` with dry run, plus
   unit tests for validation. **CHECKPOINT 2** — show a dry-run report.
3. `chart.py` + `chart_additions.json`. **CHECKPOINT 3** — dry run, then
   apply on `frontend` only after the user says yes.
4. `company.py` + `company_defaults.json`. **CHECKPOINT 4.**
5. `fiscal.py`, `payments.py`, `banking.py` with their data. **CHECKPOINT 5.**
6. `after_migrate` hook, README "How to run" and "Ownership" sections, open
   the PR to `main`. Do **not** add the app to `aig-erpnext-infra/apps.json`;
   that is a separate PR the user opens after review.

## 9. Definition of done

- `bench --site frontend install-app aig_finance` works on a site that already
  has `custom_theme`, `aig_ethiopian_calendar` and `aig_hr`.
- Dry run lists every entry with its ref and status; applying twice reports
  `unchanged` the second time.
- `docker diff $(scripts/dev.sh ps -q backend) | grep -E 'apps/(frappe|erpnext|hrms)/'`
  shows nothing but `__pycache__`.
- `git grep -nE "frappe-bench/apps/(frappe|erpnext|hrms)"` finds nothing
  that writes into core.
- Tests pass: `bench --site frontend run-tests --app aig_finance`.
- README explains, for a non-developer, what each data file controls and
  which decision ref it implements.
