# AIG Procurement & Payment Refinement — Change Log

**Scope:** Phase 3 of the AIG ERPNext v16 rollout — refined brief Sections 3.1–3.4, 4.1, 4.2 (Procurement & Payment workflows) for company **Adama Investment Group (AIG)**, site `frontend`.
**Date:** 2026-09-26
**Core-file statement:** ✅ **No core frappe/erpnext files were modified.** Every change below is a custom field, custom DocType, Workflow record, Server Script, master-data record, or configuration change inside the site database, applied by scripts in `~/aig-erp-config/scripts/`.

Every item is classified as one of:
- **[Already existed]** — present before this phase and left as-is (listed for the audit trail).
- **[Corrected]** — existed from an earlier phase but was wrong or broken; fixed in this phase.
- **[Newly built]** — created in this phase.

---

## 1. Section 3.1 — Material Request Enterprise-Head Endorsement gate (> ETB 750,000)

| Item | Class | Detail |
|---|---|---|
| `aig_estimated_total` (Currency) custom field on Material Request, label "Estimated Total (ETB)" | **[Newly built]** | Field the officer fills with the ETB estimate; drives the gate. *(This is Open Confirmation #2 — see §8.)* |
| Workflow states `Pending Enterprise Head Endorsement`, `Endorsed` on `AIG Stock Request Approval` | **[Newly built]** (phase step 131) | Endorsement stage before the normal approval flow. |
| Transitions: Draft —[Submit for Endorsement]→ Pending Enterprise Head Endorsement (cond > 750,000); —[Endorse]→ Endorsed; —[Reject]→ Rejected | **[Newly built]** (131) | |
| Procurement-Officer bypass condition corrected to `... and (doc.aig_estimated_total or 0) <= 750000` | **[Corrected]** (131) | Officer bypass no longer swallows > 750,000 requests. |
| Condition syntax: `flt(...)` → `(doc.x or 0)` in all conditional transitions | **[Corrected]** (133e) | `flt` is **not** in the workflow safe-eval globals; every MR/PO save with a conditional transition crashed with `NameError: name 'flt' is not defined` (latent since 131). |
| `Pending Enterprise Head Endorsement` state doc_status 0 → 1 | **[Corrected]** (133e) | v16 rejects 0→2 transitions, so the endorsement **Reject** button was dead. Submit-on-entry also matches the phase-1 store-review/enterprise-approval pattern. |
| Roles: AIG Procurement Officer (submit/endorse-entry), AIG Enterprise Head (Endorse/Reject) | **[Already existed]** (role doctypes) + **[Newly built]** (transitions) | |

## 2. Section 3.2 — PO Proforma committee sign-off (single committee approval — revised 2026-09-27)

| Item | Class | Detail |
|---|---|---|
| Custom DocType **AIG Committee Signoff** (parent_po → PO, committee_member → User, decision Approve/Reject, decision_date, comments) | **[Newly built]** (132) | One row per member per PO, enforced by script. |
| Server Script **AIG - CS Guard** (Before Save on AIG Committee Signoff) | **[Newly built]** (132) | Member = session user unless Administrator pre-seeds; decision ∈ {Approve, Reject}; PO must be in `Pending Committee Signoff`; one row per member; date defaults to today. |
| Server Script **AIG - PO Committee Majority** (Purchase Order, **Before Save (Submitted Document)**) | **[Newly built]** (132), **[Corrected]** (133e/134b), **[Revised]** (136/146/148) | Enforces (rule revised 2026-09-27): **the committee member's workflow click IS the approval** — one member approves on behalf of all, and their Approve sign-off row is auto-recorded (an existing row for that member is reused; manual rows keep working); 2 distinct Reject rows force Rejected; > 750,000 additionally requires the referenced MR to be Endorsed/Approved. Corrections: (a) sandbox rewrite — `getattr` is banned and crashed **every** PO save (133e); (b) moved from *Before Validate* to *Before Save (Submitted Document)* after the sign-off states became submit-on-entry (134b); (c) 2-of-3 majority relaxed to single-approval (136, verified by 137); (d) click = decision with auto-recorded row (146); (e) Rejected exits moved out of this script — they arrive via `doc.cancel()`, which never fires `before_update_after_submit` (found by probe 147 C2) — and are enforced by the new Reject Guard (148). Previous state is read from the DB. |
| Server Script **AIG - PO Committee Reject Guard** (Purchase Order, **Before Cancel**) | **[Newly built]** (148) | The committee **Reject** click lands the PO in Rejected (doc_status 2) through document cancellation, so the majority script never sees it. This guard enforces the TWO-member rejection: each member first records their 'Reject' row, then clicks 'Reject' (row + click, per member). The row flow is deliberate — the sandbox **removes `frappe.db.commit`** from Server Scripts, so a row recorded during a bounced click would vanish with the rollback. Administrator cancels skip the rule. Messages name exactly what is missing at each step (verified 9/9 by 147). |
| Workflow `AIG Procurement Approval` rewritten: Draft → Pending Committee Signoff (≥ 20,000) or Pending Finance Signoff (< 20,000) → (committee) Pending Enterprise Head Approval ≤ 750,000 / Pending Corporate Approval > 750,000 → … → Approved; Rejected from every stage | **[Newly built]** (132) | Demo chain for leadership: committee → Corporate → CEO → Approved. |
| `Pending Committee Signoff` / `Pending Finance Signoff` doc_status 0 → 1 | **[Corrected]** (133e) | Committee/Finance **Reject** buttons were dead (0→2 invalid in v16). |

## 3. Section 3.3 — Bulky / Open Tender chain (Corporate → CEO after MR endorsement)

| Item | Class | Detail |
|---|---|---|
| Transitions Pending Corporate Approval —[Approve]→ Pending CEO Approval → Approved; Reject → Rejected | **[Newly built]** (132) | |
| Bulky precondition inside AIG - PO Committee Majority: > 750,000 forwards only when the upstream MR is Endorsed/Approved, with a specific message naming the MR | **[Newly built]** (132/133e) | Acceptance S6 proves the block on an unendorsed MR. |

## 4. Section 3.4 — Model 42 mandatory attachment on Purchase Receipt

| Item | Class | Detail |
|---|---|---|
| Custom field `model_42_handover_document` (Attach) on Purchase Receipt, label "Model 42 - Signed Handover Document (required before submission)" | **[Newly built]** (133) | |
| Server Script **AIG - Model 42 Guard** (Purchase Receipt, Before Submit) | **[Newly built]** (133) | Blocks submission without the attachment; the payment side re-checks it (Three-Way Match leg 6). |

## 5. Section 4.1 — Three-Way Match on Payment Entry

| Item | Class | Detail |
|---|---|---|
| Server Script **AIG - Payment Three-Way Match** v5 (Payment Entry, Before Submit) | **[Corrected]** (133→133e) | Existed as v3/v4; v5 adds the withheld-amount leg and fixes the sandbox-safe messages. Legs: (1) Pay; (2) ≥ 1 PI reference with allocation; (3) cash paid + withheld (negative deductions) reconciles with the invoice allocation (tolerance 0.5 %, min ETB 10); (4) every invoice line linked to a PO; (5) ≥ 1 submitted Purchase Receipt per PO; (6) every PR carries Model 42. |
| Distinct error messages per leg, no `str.format` (RestrictedPython) | **[Corrected]** | v3 would have crashed with "format is an unsafe attribute" instead of showing real errors. |

## 6. Section 4.2 — VAT 15 % on invoice; VAT-WH 7.5 % + WHT 3 % at payment

| Item | Class | Detail |
|---|---|---|
| Tax template `Ethiopia Tax - AIG` (2131 - VAT Payable 15 %, On Net Total) | **[Already existed]** (earlier phase) | Verified: PI grand = net × 1.15. |
| TWC categories `AIG 7.5% VAT Withholding` (→ **2132 - VAT Withholding Payable 7.5% - AIG**) and `AIG 3% Withholding Tax` (→ **2133 - Withholding Tax Payable 3% - AIG**), with account rows and rate rows | **[Corrected]** (133/133c) | Categories and accounts existed from earlier phases; the missing posting-account rows were added and verified. |
| Server Script **AIG - Payment Withholding 7.5% + 3%** (Payment Entry, Before Validate) | **[Newly built]** (133e/134c) | Books the two withholdings as negative PE deductions and **enforces the net cash figure** (paid = Σ PI allocations − withheld). Verified GL for a 800,000 net invoice: party DR 920,000 · bank CR 836,000 · 2132 CR 60,000 (7.5 %) · 2133 CR 24,000 (3 %), difference 0. |
| Suppliers carry **no** `tax_withholding_category` default | **[Newly built]** (deliberate design) | The v16 auto-TDS engine applies only ONE category and only on unallocated amounts; supplier-level defaults would double-withhold. Both withholdings are computed by the script above instead. *(Basis for Open Confirmation #1 — see §8.)* |
| Company default **Stock Received But Not Billed** (account created + set) | **[Corrected]** (133e) | Missing default blocked all PR/PI submissions. |
| Company default **Round Off** (account created + set) | **[Corrected]** (133e) | Missing default blocked PI submission. |
| User-permission cleanup: rows with allow=Cost Center but applicable_for=Company pointing at a cost center ("Head Office - AIG" is not a company) deleted | **[Corrected]** (133e) | Those rows failed every per-document read for scoped demo users once user-permission checks ran on saved docs. |
| Custom DocPerm: Purchase Receipt += **Stock User** and **AIG Store Keeper** (create/submit), Purchase Invoice += **Accounts User** (create/submit) | **[Corrected]** (144) | The AIG-only custom permission sets silently disabled standard storekeeper receiving and finance invoicing (plain role grants had no effect — custom DocPerms replace standard rows). Restores frappe's standard expectation for the demo; AIG roles' rights untouched. Verified by 145 (4/4 with real users). |
| Server Script **AIG - MR End User Type Default** (phase-1, Before Insert): the silent End-User conversion to Material Issue now shows a visible notice | **[Corrected]** (153) | Policy unchanged (End Users raise stock requests only; Purchase belongs to Procurement — enforced by the phase-1 Type Guard), but the invisible conversion read like a bug during demo rehearsals ("I selected Purchase and it changed"). The save now announces the conversion. Demo consequence: the **Procurement Officer raises Purchase MRs** (with *Requested By* naming the employee). Verified both branches (153): enduser+Purchase → Material Issue + notice; officer+Purchase → stays Purchase. |
| Cost center **Construction Projects Phase 1 - AIG** (leaf) created under Construction Projects; construction warehouses re-pointed to it | **[Corrected]** (133e) | Construction Enterprise / Construction Projects were both groups with no leaf child, so construction users could not transact at all. |
| Budgets (Section 5 of the brief) | **[Already existed]** — none | Budget list is empty (0 records); the MR `aig_budget_checked` / `aig_budget_note` fields remain informational. Flagged here rather than silently skipped. |

## 7. Acceptance evidence (Section 7)

`134_acceptance_run.py` — **25/25 checks passed** (re-run after the 136/146/148 committee revision), all negative cases assert the exact user-facing message, all positive chains walked by the real demo users, full cleanup verified (no test residue). Key proofs:

- S1/S3: officer bypass allowed ≤ 750,000, blocked > 750,000 (no bypass action offered).
- S2: endorsement path reaches **Endorsed** (docstatus 1).
- S4: the committee member's **click is the approval** — a direct click (no pre-recorded row) auto-records their Approve sign-off, finalizes the PO, and the Enterprise Head approves it — **single-approval rule** (136/146/148).
- S5: 2 Reject rows block Finalize and enable the committee Reject (reject = row + click by two members; rule unchanged).
- S6: > 750,000 Forward blocked while the MR is unendorsed ("Bulky/Open Tender: … not yet endorsed").
- S7: endorsed bulky chain → committee → Corporate → CEO → **Approved**.
- S8: PR submit blocked without Model 42.
- S9: PI VAT math exact; auto-TDS inert.
- S10–S14: each broken payment leg yields its own specific Three-Way-Match message; raw submits are blocked by the guard; overpay attempts are neutralized to the net figure.
- S15: full clean chain with GL assertions — party DR grand, 2132 CR 7.5 % net, 2133 CR 3 % net, bank CR net, difference 0.
- S16: CEO-wording audit clean on all custom fields.

## 8. Open confirmations (Section 8 of the brief)

1. **Finance sign-off on the tax calculation.** The 15 % VAT / 7.5 % VAT-WH / 3 % WHT wiring and the payment-time GL treatment (§6) match the brief's numbers, but per the brief this remains **pending Finance's formal confirmation**. Specifically to confirm: (a) withholding base = VAT-exclusive invoice net; (b) single payment entry books both withholdings (vs. two separate entries); (c) negative-deduction presentation on the PE vs. the stock TDS engine.
2. **Estimated-total field choice.** The brief asked for a decision on where the > 750,000 estimate lives. Decision made: **new custom Currency field `aig_estimated_total` ("Estimated Total (ETB)") on Material Request** (not derived from item rates), because the endorsement gate must fire before rates are reliably entered. To be countersigned by Finance/Procurement.

## 9. Script inventory for this phase (all in `~/aig-erp-config/scripts/`)

`131_mr_endorsement_gate.py` · `132_po_committee_signoff.py` · `133_model42_and_threeway_v4.py` · `133c_twc_wire_accounts.py` · `133d_withhold_probe.py` (rollback probe, commits nothing) · `133e_withhold_wire.py` · `134_acceptance_run.py` (commits only its own log) · `134b_majority_event.py` · `134c_withhold_paid_fix.py` · `135_changelog_facts.py` (read-only) · `136_committee_single_approve.py` (single-approval rule) · `137_single_approve_verify.py` (5/5, self-cleaning) · `138/139/141/142/142b/143` (read-only probes) · `140_demo_setup.py` (demo supplier/item + role grants) · `144_unblock_demo_perms.py` (Custom DocPerm fix) · `145_demo_smoke.py` (4/4 permission-enforced demo smoke, self-cleaning) · `146_committee_click_approval.py` + `148_committee_reject_guard.py` (click = approval; Before Cancel reject guard) · `147_committee_click_verify.py` (9/9, self-cleaning) · `149–151` (demo diagnosis + demo-MR reset) · `152/152b` (read-only MR-type default probes) · `153_end_user_type_notice.py` (visible End-User conversion notice).

## 10. Known cosmetic behaviour (no action needed)

- Every real traceback from `bench execute` is followed by `NameError: name 'custom_theme' is not defined` — a bench artifact, not a script failure.
- Direct "Submit" on PO/PE drafts is intentionally blocked ("only allowed through the AIG … workflow actions") — the workflow buttons are the intended path.
