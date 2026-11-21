# Build brief, phase 2: everything financial lives in `aig_finance`

Paste this to the coding agent after phase 1 (the review fixes) is merged.
Rules in `knowledge.md` still apply. Work on `feature/<topic>` branches, one PR
per numbered step, and stop for review after each.

## Goal

A brand-new site, after `bench install-app aig_finance` and `bench migrate`,
ends up with the complete AIG finance setup, with nobody running scripts by
hand. A push merged into `main` of `aig-finance` reaches the server through the
deploy pipeline and every developer through `sync-pull.sh`.

Today that setup is spread over one-off scripts. They move into the app as
data files + appliers, and the scripts are retired:

| Today | Moves to |
| --- | --- |
| `aig-erp-config/scripts/00a_create_company.py` | `data/company.json` + `setup/bootstrap.py` |
| `AIG_Corrected_Demo_CoA.csv`, scripts `190`, `83`, `84`, `86` | `data/chart_of_accounts.csv` + `setup/bootstrap.py` |
| script `191` (non-stock parts), `194` fiscal years | existing `company_defaults.json`, `fiscal_years.json` |
| `custom_theme/aig_custom_theme/setup/ensure_tax_setup.py` | `data/taxes.json` + `setup/taxes.py` |
| tax-related rows in old `custom_theme/aig_setup_01.py` | `data/taxes.json` |

Stock (warehouse accounts, scripts 191/192 stock parts) and cost centers / org
units (aig_hr's `company_configuration.json`) stay where they are.

## 1. Bootstrap: company and chart (`setup/bootstrap.py`)

`data/company.json`: company name, abbreviation `AIG`, currency `ETB`, country
Ethiopia, `tax_id` (empty until finance provides it), `status`.

Order inside `bootstrap.apply`, each step skipped when already done:

1. Company missing and entry approved → create it with ERPNext's standard
   chart (the only way ERPNext creates a company).
2. Account `21402` missing → replace the standard chart with
   `data/chart_of_accounts.csv` (the 219-row AIG chart plus the 13 approved
   additions, as one file) using
   `erpnext.accounts.doctype.chart_of_accounts_importer.chart_of_accounts_importer`.
   Before importing, clear the links that block the importer from deleting
   the standard accounts (what script 190 does: Expense Claim Account and Mode
   of Payment Account rows, tax templates of the company), then report any
   link that remains instead of forcing.
3. **Hard safety rule:** never touch the chart when the company has any GL
   Entry, Stock Ledger Entry or Payment Ledger Entry. Report `error` and stop.
4. Re-run the company defaults applier afterwards (the import resets some
   Company fields).

`chart_additions.json` stays for accounts added after go-live; at bootstrap
they are already part of the CSV.

## 2. Taxes (`setup/taxes.py`, `data/taxes.json`)

Ownership changes: tax moves from the planned `aig_tax` app into `aig_finance`.
Update the ownership table in `knowledge.md` and README.

- Sales Taxes and Charges Template `Ethiopia VAT 15%`: one row, On Net Total,
  15%, account 21402 (D-10). `is_default` per decision.
- Purchase Taxes and Charges Template `Ethiopia VAT 15%`: one row, 15%,
  account **12201** VAT Receivable (D-11). The current theme script posts it
  to 21402; that is the bug this fixes.
- Tax Withholding Categories: `AIG 3% Withholding Tax` → 21403, thresholds
  ETB 20,000 goods / 10,000 services (D-12, P-9); `AIG 7.5% VAT Withholding`
  → 21401 (D-13, only if AIG is a VAT withholding agent).
- Tax Category and Tax Rule only if the decision doc asks for them.
- Same entry shape as the other data files (`ref`, `status`), dry run by
  default, idempotent, report per object.
- Templates are matched by name and company; rows are reset to the data file
  (the template is configuration, it holds no postings).

When this is merged and deployed, open a PR in `aig-erp-theme` that removes
`ensure_tax_setup.py` and its hooks/notes. Do not remove it before.

## 3. Retire the scripts

- In `aig-erp-config`, move the superseded scripts to `scripts/retired/` with
  a README line each pointing to the aig_finance file that replaced it.
- In `aig-erp-theme`, propose (separate PR) moving `custom_theme/aig_setup_00.py`
  … `aig_setup_08.py` out of the app: they are one-time build scripts whose
  results are now fixtures. List any record they create that is NOT covered
  by a fixture or by aig_finance before removing them.

## 4. Proof (definition of done)

On the local dev stack:

```bash
~/aig-erpnext-infra/scripts/reset-site.sh local      # fresh site, all apps
~/aig-erpnext-infra/scripts/dev.sh exec -T backend bench --site frontend execute aig_finance.setup.apply.run
```

The dry run after the reset must show `unchanged` for every approved entry
(the after_migrate hook already applied them), and:

- the company exists with 219 + approved accounts, account 21402 present;
- purchase VAT template posts to 12201, sales to 21402;
- GL Entry count 0;
- a second `migrate` changes nothing (`unchanged` everywhere).

Paste that output into the PR.
