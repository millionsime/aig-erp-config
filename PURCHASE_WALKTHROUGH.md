# AIG Purchase-to-Payment — Live Demo Walkthrough

**Purpose:** a click-by-click script for showcasing the entire AIG procurement & payment flow in ERPNext v16, one user at a time, with the "wow moments" (system-enforced controls) called out so you can pause on them.

**The story you are telling (TODAY, 2026-09-29):** use **TRACK B** first — an employee raises a 15,000 purchase themselves, the Enterprise Head approves, the Store Manager approves and assigns the buyer, the purchaser's small PO gets Finance's sign-off directly. Then **TRACK A** (Acts 1–8) shows the big purchase climbing the full ladder: Procurement Officer raises it for an employee (**Requested By** = the end user) → Enterprise Head (endorsement) → Purchase Committee (**one member approves on behalf of all — revised rule, 2026-09-27**) → Corporate → CEO → Store (Model 42) → Finance (VAT) → Payment with double withholding → the books balance themselves. Finish with the seeded books (income in 9 cost centers, Trial Balance diff 0.00).

**Site:** `frontend` · **Company:** Adama Investment Group · **All passwords:** `aig2026` · **URLs:** `https://<your-host>/app` (web) — every login below lands on the Desk home.

**Numbers to remember (they repeat as proof):**

| Stage | Figure |
|---|---|
| Net (PO / PI) | **800,000** |
| VAT 15% → Grand total | 120,000 → **920,000** |
| VAT Withholding 7.5% (of net) | **60,000** |
| Withholding Tax 3% (of net) | **24,000** |
| Actual cash paid | **836,000** |

---

## 0. Setup — everything below is ALREADY DONE (verify once, 2 minutes)

You do not need to create anything live. The one-time setup script (140/144/145) already created and verified all of this. Just eyeball it:

1. **Log in as `Administrator` once** (or any user) and confirm the demo masters exist:
   - **Supplier list** (`/app/supplier`): `Adama Trading PLC` ✔
   - **Item list** (`/app/item`): `AIG-DEMO-LAPTOP` — "Laptop Pro 15-inch (demo)" ✔
2. **Nothing else.** Cost centers, warehouses, workflows, withholding accounts (2132/2133), the tax template, and every demo user are live from the earlier phases.

**If you ever re-create a bare site**, run these two scripts (they are idempotent):
```bash
wsl -d Ubuntu -- bash -lc "bash /home/milli/aig-erp-config/scripts/run_script.sh /home/milli/aig-erp-config/scripts/140_demo_setup.py"
wsl -d Ubuntu -- bash -lc "bash /home/milli/aig-erp-config/scripts/run_script.sh /home/milli/aig-erp-config/scripts/144_unblock_demo_perms.py"
```

**Demo-day habits:**
- Keep two browser windows (or use private/incognito for each new login) so switching users takes seconds.
- Between demo runs, the previous run's documents will be lying around at their last stage — for a clean run, either continue from them or delete the drafts (drafts only) as Administrator.
- If a workflow button you expect is missing, you are logged in as the wrong user — that is itself a demo point.

**Cast & who does what:**

| User | Password | Role in the story |
|---|---|---|
| `enduser.agro@aig.local` | aig2026 | The employee who needs the laptops (named in **Requested By**; their own stock requests take the store route — see the Act 1 note) |
| `procurement.agro@aig.local` | aig2026 | Procurement Officer (creates MR in reality? no — creates PO, fires the workflow) |
| `head.agro@aig.local` | aig2026 | Enterprise Head (endorsement + final PO approval) |
| `committee1@aig.local` | aig2026 | Purchase Committee member (**the one who approves for all**) |
| `committee2@aig.local` | aig2026 | Second committee member (only for the optional reject demo) |
| `corporate@aig.local` | aig2026 | Corporate (bulky chain) |
| `ceo@aig.local` | aig2026 | CEO (top of the chain) |
| `storekeeper.agro@aig.local` | aig2026 | Store Keeper (goods receipt + Model 42) |
| `finance@aig.local` | aig2026 | Finance (invoice + payment initiation) |
| `deputy@aig.local` | aig2026 | Deputy (payment approval) |
| (corporate / ceo again) | — | Payment approval chain |
| `auditor@aig.local` | aig2026 | Auditor (closing proof, read-everything) |

---

# TRACK B — End-user-initiated purchase (NEW policy, live 2026-09-29)

> **Supersedes the officer-first note in Act 1.** As of 2026-09-29, End Users CAN raise
> Purchase requests. New route: End User → **Enterprise Head** → **Store Manager (approves
> AND assigns the purchaser)** → Purchaser creates the PO → <20,000 PO goes **direct with
> Finance Sign-off**. Old Material Issue (Model 19) store route and the officer routes
> (Acts 1–8) still work unchanged. Verified 10/10 by `scripts/176_enduser_route_verify.py`.

## ACT B1 — The request (End User)

**Login:** `enduser.agro@aig.local` / `aig2026`

1. Home → **Buy** → **Material Request List** → **+ Add Material Request**.
2. Fill exactly:
   - **Purpose:** `Purchase`  ← now permitted for end users (scope guard allows Purchase or Material Issue only — anything else throws).
   - **Company:** `Adama Investment Group`
   - **AIG Cost Center:** `Animal Feed Factory - AIG`
   - **Estimated Total (ETB):** `15,000`  *(keep below 20,000 so the PO takes the direct path in Act B4)*
   - **Item table:** `AIG-00001` Managerial Chair, Qty `15`, Rate `1,000`, Warehouse `Animal Feed Plant - AIG`.
3. **Save** → the workflow button **Submit Purchase Request** appears (this is the NEW end-user purchase button).
4. Click it → State: **Pending Head Approval**.

**🎤 WOW:** *"The same employee can raise two kinds of requests: a Model 19 stock issue routes to the store; a purchase routes to the enterprise head. I never choose the route — the request type routes itself. And if I tried a 'Manufacture' or 'Transfer' request, the system would refuse — end users raise purchases or stock issues, nothing else."*

## ACT B2 — The Enterprise Head approves (head.agro@aig.local)

**Login:** `head.agro@aig.local` / `aig2026`

1. Open the request (Pending Head Approval) → buttons **Approve** / **Reject**.
2. Click **Approve** → State: **Pending Store Review**.

**🎤 WOW:** *"Separation of duties is structural: the person who asked can never approve their own request — the guard blocks it even at this desk. And the head does not choose the buyer: approval just moves it to stores."*

## ACT B3 — Store Manager approves AND assigns the purchaser (storeadmin.agro@aig.local)

**Login:** `storeadmin.agro@aig.local` / `aig2026`

1. Open the request → scroll to **Assigned Procurement Officer**.
2. Pick `procurement.agro@aig.local`.
3. The button **Approve & Assign** only exists because an officer is selected — that's the control. Click it.
4. State: **Approved**, with the buyer's name stamped on the request.

**🎤 WOW:** *"No anonymous purchases. Stores cannot approve without naming the purchaser, and the purchaser is now on the record — permanently."* (Optional negative: clear the field — the button disappears.)

## ACT B4 — The purchaser creates the PO < 20,000 (procurement.agro@aig.local)

**Login:** `procurement.agro@aig.local` / `aig2026`

1. Open the Approved request → **Create → Purchase Order** (links the MR automatically).
2. Supplier: `Blue Nile Trade PLC`; confirm the row (Qty 15 × 1,000 = 15,000) → **Save**.
3. The button shows **Submit for Direct Purchase** — it appears precisely because the PO is under 20,000. Click it.
4. State: **Pending Finance Signoff**.

**Login:** `finance@aig.local` / `aig2026` → open the PO → **Finance Sign-off** → State: **Approved**.

**🎤 WOW (the amount contrast):** *"Same officer, two destinies: this 15,000 PO needed only Finance's sign-off — but change one digit to 25,000 and the committee, and past 750,000 the Corporate CEO ladder appears (Track A). The buttons ARE the policy."*

> **Continue the story:** from here the Track B PO flows through Acts 5–8 unchanged (receipt + Model 42 → VAT invoice → payment chain → GL proof). Or jump to the accounting finale with the seeded books.

---

## ACT 1 — The purchase request (Procurement Officer)

**Login:** `procurement.agro@aig.local` / `aig2026`

1. Home → **Buy** (or search "Material Request") → **Material Request List** → **+ Add Material Request**.
2. Fill exactly:
   - **Purpose:** `Purchase`  ← **CRITICAL. Leave it as Purchase.**
   - **Company:** `Adama Investment Group`
   - **AIG Cost Center:** `Animal Feed Factory - AIG`
   - **Estimated Total (ETB):** `900,000`  *(drives the endorsement gate — keep it above 750,000)*
   - **Requested By:** `enduser.agro@aig.local`  *(the employee who needs the laptops — the audit trail keeps them in the story)*
   - **Required By / Transaction Date:** today (defaults)
   - **Item table:** `AIG-DEMO-LAPTOP`, Qty `10`, UOM `Nos`, Warehouse `Animal Feed Plant - AIG`, Rate `80,000`
3. **Save.** The doc gets a name like `MAT-MR-2026-…` and stays Draft.

**⚠️ Why the OFFICER starts the story (deliberate AIG control):** End Users may only raise **stock requests** — the system always records their MRs as **Material Issue** (Model 19), even if they pick Purchase (a yellow notice now says exactly that on save), and those take the store route, not this one. Purchase-type requests belong to Procurement. Trying to "fix" the story by logging in as the end user will dead-end the demo — keep the officer as the author.

**🎤 Say:** *"An employee asked for 10 laptops. I'm raising the purchase request for them — and watch what the system does with an expensive one: I never choose the route, the route chooses itself."*

> **Optional pre-demo wow (do it now, as the officer):** save a SECOND MR identical but **Estimated Total = 100,000** (Purpose still `Purchase`, just Save — no button). In Act 2 it shows **Submit Request** (→ Approved, no ceremony) while the laptop request shows **Submit for Endorsement** only — that contrast IS the control.

---

## ACT 2 — The endorsement gate (Procurement Officer → Enterprise Head)

**Login:** `procurement.agro@aig.local` / `aig2026`

1. Open the MR from Act 1 (Material Request List → your doc). It must show **Draft**.
2. Click the workflow button **Submit for Endorsement** — it is there *because* the estimate exceeds 750,000. On a cheap request the same officer sees **Submit Request** instead (see the contrast below) — there is **no bypass button** for bulky purchases.
3. State becomes **Pending Enterprise Head Endorsement**. The document is now submitted (read-only content) — highlight that nothing is editable anymore.

**🎤 WOW MOMENT (the honest version, works live):** open one of the officer's own cheap drafts (e.g. `MAT-MR-2026-00011`, estimate 3,422) — its button is **Submit Request → Approved**, no endorsement. Back on the 900,000 laptop request: **Submit for Endorsement** only. *"Same officer, same screen — the amount alone changes the buttons. A bulky purchase cannot skip the Enterprise Head, because the bypass button simply is not offered."*

**Login:** `head.agro@aig.local` / `aig2026`

4. Open the same MR → click **Endorse**.
5. State: **Endorsed**. 

**🎤 Say:** *"Over 750,000 birr needs the Enterprise Head's endorsement before procurement may even price it."*

> **If you see NO buttons as the officer:** check the MR's state. `Pending Store Review` means the request was recorded as **Material Issue** — that happens when an **End User** raised it (policy auto-conversion, see the Act 1 note) or Purpose was non-purchase; those take the store route and can never enter this flow — delete the doc (or ask me to) and raise it as the officer. Otherwise: wrong user for this state — the buttons are the role.

---

## ACT 3 — The PO and the committee (Procurement Officer → Committee)

**Login:** `procurement.agro@aig.local` / `aig2026`

1. Home → **Buying** → **Purchase Order** → **+ Add Purchase Order**.
2. Fill:
   - **Supplier:** `Adama Trading PLC`
   - **Company:** `Adama Investment Group`
   - **AIG Cost Center:** `Animal Feed Factory - AIG`
   - **Item:** `AIG-DEMO-LAPTOP`, Qty `10`, Rate `80,000`, Warehouse `Animal Feed Plant - AIG`
   - In the item row, **Material Request:** pick the MR from Act 1 (important for the bulky rule later).
3. **Save.** Check **Grand Total = 800,000** on the right.
4. Click **Submit for Committee Review** (the ≥ 20,000 path; < 20,000 would go to Finance Sign-off instead — mention it).
5. State: **Pending Committee Signoff** (submitted).

**Login:** `committee1@aig.local` / `aig2026`

6. Open the PO and click **Finalize Committee Decision** (≤ 750,000) — for THIS story the total is 800,000, so instead click **Forward to Tender Committee**. **That single click IS the approval** — no extra form to fill.

**🎤 WOW MOMENT — the headline of the demo:** *"The rule used to be 2-of-3 committee members with paper sign-offs. Management changed it: ONE member now approves on behalf of all — and the click itself IS the approval. Watch: I never filled any sign-off form."*
7. Show the proof: on the PO, scroll to the related **AIG Committee Signoff** list — the system **auto-recorded one row**: member = the member who clicked, decision = Approve, today's date. Exactly one row, one member, zero paperwork.

> **Negative wow — rejection still needs TWO members (optional, recommended):** on a fresh PO in this state, log in as `committee1` and click **Reject** directly → bounced: *"…a committee rejection needs TWO members. Record your 'Reject' sign-off first (AIG Committee Signoff → Add), then click 'Reject' again. 0 of 2 'Reject' sign-offs are recorded."* Committee1 records their `Reject` row (Decision: `Reject` → Save), clicks **Reject** again → bounced again, now precise: *"…your 'Reject' sign-off is recorded - one MORE committee member must record their 'Reject'… 1 of 2 recorded."* Now `committee2` records their `Reject` row, and `committee1` clicks **Reject** once more → **Rejected**. ("One member approves for all — but it still takes two of us to say no.")

---

## ACT 4 — Corporate and CEO (the bulky chain)

State is **Pending Corporate Approval**.

**Login:** `corporate@aig.local` / `aig2026`
1. Open the PO → click **Approve** → **Pending CEO Approval**.

**🎤 WOW MOMENT (bulky rule — optional but strong):** before this, if the MR from Act 1 were NOT endorsed, this Forward would have been thrown back: *"AIG Bulky/Open Tender: Material Request … is not yet endorsed by the Enterprise Head."* You endorsed it in Act 2, so the chain is open — connect the dots for the audience: the endorsement from 20 minutes ago is a precondition HERE.

**Login:** `ceo@aig.local` / `aig2026`
2. Open the PO → click **Approve** → **Approved**.

**🎤 Say:** *"Over 750,000: committee says yes, Corporate says yes, the CEO says yes. Under 750,000, the Enterprise Head alone would have closed it."*

---

## ACT 5 — Goods receipt + Model 42 (Store)

**Login:** `storekeeper.agro@aig.local` / `aig2026`

1. **Stock** → **Purchase Receipt** → **+ Add Purchase Receipt**.
2. Fill: Supplier `Adama Trading PLC`, Company, **Cost Center** `Animal Feed Factory - AIG`; item row: `AIG-DEMO-LAPTOP`, Qty `10`, Rate `80,000`, Warehouse `Animal Feed Plant - AIG`, **Purchase Order:** the PO.
3. **Save**, then click **Submit** — **nothing happens / you get an error**, because:

**🎤 WOW MOMENT:** **Model 42.** The field **"Model 42 - Signed Handover Document (required before submission)"** is empty. Attach any small PDF/jpg from your desktop, click **Submit** again → accepted. *"No signed Model 42 handover document, no goods receipt. This is the custom control AIG asked for — the store physically cannot skip it."*

---

## ACT 6 — The invoice with VAT (Finance)

**Login:** `finance@aig.local` / `aig2026`

1. **Accounts** → **Purchase Invoice** → **+ Add Purchase Invoice**.
2. Fill: Supplier `Adama Trading PLC`, **Taxes and Charges:** `Ethiopia Tax - AIG`, Cost Center as before; item row: the item, Qty `10`, Rate `80,000`, **Purchase Order:** the PO.
3. **Save.** The Taxes and Charges table fills automatically: **VAT 15% → 120,000**; **Grand Total = 920,000**.
4. **Submit.** (Hold the payment thought: suppliers do NOT carry a withholding category here — that is deliberate; both withholdings are computed at payment so nothing double-counts. Say that if asked.)

**🎤 Say:** *"15% VAT on the net — 800,000 becomes 920,000 — exactly the statutory math."*

---

## ACT 7 — Payment with double withholding (Finance → Deputy → Corporate → CEO)

**Login:** `finance@aig.local` / `aig2026`

1. **Accounts** → **Payment Entry** → **+ Add Payment Entry**:
   - Payment Type: `Pay`, Party: `Adama Trading PLC`
   - **Get Paid Amount / references:** pull the Purchase Invoice (allocated 920,000)
   - Reference No/Date: any ("DEMO-001", today)
2. **Save** — the custom withholder instantly rewrites the cash: **Paid Amount = 836,000** and two negative **Deductions** rows: `2132 - VAT Withholding Payable 7.5% - AIG`: **−60,000**, `2133 - Withholding Tax Payable 3% - AIG`: **−24,000**.
3. Click **Submit for Deputy Review**.

**🎤 WOW MOMENT:** *"920,000 is owed, but only 836,000 leaves the bank. 60,000 VAT-withholding and 24,000 withholding tax stay with us, booked to 2132 and 2133 — and the system FORCES the cash number; a finance officer cannot type 920,000 by hand."* (Bonus wow: attempt to set Paid Amount = 920,000 manually before saving, save — the withholder snaps it back to 836,000.)

**Approval walk (fast, one login each):**
4. `deputy@aig.local` / aig2026 → open the PE → **Approve** → Pending Corporate Approval.
5. `corporate@aig.local` → **Approve** → Pending CEO Approval.
6. `ceo@aig.local` → **Approve** → **Approved** (submitted).

---

## ACT 8 — The closing proof (Finance shows the books)

**Login:** `finance@aig.local` / `aig2026` *(the same finance window — they own the payment)*

1. Open the Payment Entry → click **View > Ledger / General Ledger** (or Reports → General Ledger, filter voucher = this PE).
2. Expected rows:

| Account | Debit | Credit |
|---|---|---|
| Creditors (Adama Trading PLC) | **920,000** | |
| Bank | | **836,000** |
| 2132 - VAT Withholding Payable 7.5% | | **60,000** |
| 2133 - Withholding Tax Payable 3% | | **24,000** |

**🎤 CLOSING WOW:** *"Debits = Credits. The supplier's full 920,000 is settled on paper, the bank really paid 836,000, and the 84,000 we kept from the state sits in two liability accounts. Nobody made this journal entry — the payment did."*

3. Optional finishing touch 1: hand the keyboard to `auditor@aig.local` and let them open the same Payment Entry — read-everything access for the auditor, and the demo ends with the control role.
4. Optional finishing touch 2: open the **Purchase Order** and show the audit trail (sidebar → Activity/Workflow history): End User → Officer → Endorsed → Committee (1 member) → Corporate → CEO → Store → Finance → payment. One thread, six users, every gate visible.

---

## Cheat sheet — every gate in one table

| # | Gate | User who trips it | Where in the demo |
|---|---|---|---|
| 0 | **End User CAN raise Purchase requests** — head-first route (2026-09-29 policy); store must name the buyer to approve | enduser.agro → head.agro → storeadmin.agro | Acts B1–B3 |
| 0b | End users raise **Purchase or Material Issue only** — other types throw | enduser.agro | Act B1 wow |
| 0c | **PO < 20,000 → direct path with Finance Sign-off** (committee only ≥ 20,000) | procurement.agro → finance | Act B4 |
| 1 | > 750,000 MR needs Enterprise-Head endorsement (officer has no bypass button) | procurement.agro | Act 2 |
| 2 | < 750,000 MR approves directly | procurement.agro | Act 1 optional |
| 3 | **ONE committee click approves for all (auto-recorded sign-off)**; rejection = row + click by TWO members | committee1 (+ committee2 for the reject demo) | Act 3 |
| 4 | > 750,000: committee → Corporate → CEO; MR must be endorsed (Bulky rule) | committee1 / corporate / ceo | Act 3–4 |
| 5 | Purchase Receipt submits only with Model 42 attached | storekeeper.agro | Act 5 |
| 6 | PI auto-applies VAT 15% (800,000 → 920,000) | finance | Act 6 |
| 7 | PE withholder: 7.5% + 3% of net, cash forced to 836,000; three-way match (PO→PR→PI) | finance | Act 7 |
| 8 | Payment chain Deputy → Corporate → CEO (raw submit blocked) | deputy / corporate / ceo | Act 7 |
| 9 | GL self-balances: 920,000 = 836,000 + 60,000 + 24,000 | auditor | Act 8 |

## If something misbehaves live

- **Missing workflow button:** wrong user (check the table in §0) or wrong state; the buttons literally are the role.
- **"Not a valid Workflow Action"** when raw-submitting a PO/PE: by design — use the AIG buttons.
- **Permission error while creating PR as storekeeper / PI as finance:** re-run setup scripts 140 + 144 (§0).
- **Everything else:** the acceptance run `134_acceptance_run.py` re-proves all 24 gates in one command — run it after the demo to restore a clean state.

*Rule history for the curious audience question: the committee gate shipped as 2-of-3 (brief §3.2) and was revised on 2026-09-27 to single-approval-on-behalf-of-all by management decision; rejections still require 2 members. See `PROCUREMENT_REFINE_CHANGELOG.md` §2.*
