# How to use AIG's reference documents

AIG has written papers about stock, assets and procurement. They are
**input for design, not a to-do list**. Read them to understand what the
business wants, then build only what a task asks for, the ERPNext way.

Keep the papers outside git (for example `~/aig-docs/`). Some of these
repositories are public; never commit internal papers to them.

## Order of authority (highest first)

1. `knowledge.md` rules: never touch core, everything in app files, PRs only.
2. Decisions signed by management in "AIG Finance Default Accounts:
   Decisions for Management" (refs D-01…D-31, P-1…P-10).
3. Standard ERPNext behaviour on the pinned version. Prefer configuration
   over custom code, and custom code over anything that fights the standard flow.
4. Approved AIG papers: *Stock Settings Adjustments*, *Stock and Asset
   Module Guideline v1.0*.
5. Concept notes and drafts: *AIG Purchase Order Workflow* concept note.
   Design input only, until its open questions are answered.

When two sources disagree, do not choose. List the conflict in the PR
description and ask.

## Stock Settings Adjustments (approved settings)

| Setting in the paper | What to do |
| --- | --- |
| Valuation method: Moving Average | Adopt (P-10). Only while no real item has stock movements; check first and stop if any do. The site is FIFO today. |
| Item naming by series `AIG-ITEM-YYYY` | Adopt, but `custom_theme` already generates item codes (server script "AIG - Item Auto Code", client script "AIG - Item Code Auto Hint"). Reconcile with that; never build a second generator. |
| Default Item Group: All Item Groups | Ask. That is the tree root, so items would stay unclassified and get no group defaults. |
| Auto insert price list rate if missing | Adopt. |
| Pick serial/batch based on FIFO | Adopt. |
| Notify by email on automatic Material Request | Adopt; needs an outgoing email account on the site. |

## Stock and Asset Module Guideline v1.0 (user manual)

Use it for **operating rules and controls**. It is a general manual, so:

- **Adopt:** no negative stock; over-receipt allowance 0–5% with Stock
  Manager as exception role; "Stock Frozen Up To" at each month close;
  barcode field on; a Rejected/Quarantine store for rejected quantities;
  two-step transfers through Goods In Transit; User Permissions so store
  keepers only see their warehouses; workflows on Material Request, Material
  Issue and Stock Reconciliation; Purchase Receipt → Purchase Invoice flow;
  Landed Cost Voucher for freight and duty; Auto Create Assets on Purchase;
  CWIP for assets built over time; automatic depreciation booking; opening
  stock by Stock Reconciliation against Temporary Opening (new account 14003).
- **Do not copy literally:** the sample warehouse tree (`... - ABC`): derive
  AIG's from the enterprises in `aig_hr/data/organization_structure.json`;
  the sample depreciation table (the manual itself calls it illustrative):
  use the rates management signs; the standard role names (Stock User, Stock
  Manager…): map them to existing AIG roles instead of inventing new ones.
- **Do not do:** LIFO; manual journal entries to stock or asset accounts.
- **Check the version:** parts are written for ERPNext v15 (Serial and Batch
  Bundle notes). Confirm on v16 before relying on a screen or field name.

## AIG Purchase Order Workflow (concept note, NOT approved)

Do **not** implement it yet. Its section 9 lists five open questions.
Known conflicts to raise when it is picked up:

1. **Receiving by Stock Entry instead of Purchase Receipt.** With perpetual
   inventory this skips "Stock Received But Not Billed", supplier invoice
   matching, landed costs and automatic asset creation. The guideline above
   uses Purchase Receipt. Recommend Purchase Receipt.
2. **"Add a server script and a client script."** Not as database records:
   the logic goes in `custom_theme` code (procurement is owned there).
3. **One workflow per DocType.** `custom_theme` already has Purchase Order
   committee logic ("AIG - PO Committee Majority", "AIG - PO Committee Reject
   Guard"). Extend or replace it in one place; never add a second workflow.
4. **Boundary amounts** (exactly 20,000 / 750,000, with or without VAT) are
   undecided. Do not guess.
5. **"Unlimited Direct Purchase has its own workflow"** contradicts "all five
   methods in one workflow" in the same note. Ask.
