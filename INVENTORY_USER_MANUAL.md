# AIG Inventory Management — User Manual & Leader Demo Script

**System:** ERPNext v16 · Company **Adama Investment Group (AIG)** · Currency ETB
**URL:** http://localhost:8080  (login page: `/login`, desk: `/app`)
**Status on this instance:** workflows, roles, users, print formats and guard rules are **live and verified**. Demo stock has been re-seeded after the Phase-2 clean-up.

---

## 1. What the system enforces (the 30-second version)

| Flow | Document | Approval chain | Stock effect |
|---|---|---|---|
| Stock request (Model 19) | Material Request | End User → **Main Store Admin** (budget check) → **Enterprise Head** → Approved | none until issue |
| Issue to requester (Model 22) | Stock Entry (Material Issue) | Store Keeper posts against an Approved request | decreases on Post |
| Receiving (Quality Form) | Stock Entry (Material Receipt) | Store Keeper → **General Store Keeper** → **Property Admin** → (Main Store Admin if Main Store) → Posted | increases only at Posted |
| Transfer | Stock Entry (Material Transfer) | Store Keeper posts (approval lives on the request) | moves between warehouses |
| Count / adjustment | Stock Reconciliation | reason code + note mandatory | corrects on submit |

Guards that always run (server-side, cannot be bypassed from UI or API):
- **Raw submit is blocked** — a Stock Entry must go through its workflow ("Posted" state).
- **Self-approval is blocked** — a requester can never approve their own request.
- **Over-issue is blocked** — you cannot issue more than the approved request quantity.
- **Receipts cannot skip inspection** — "Record Inspection" fails without a submitted Quality Form (Quality Inspection).
- **Rejected/damaged quantities never enter available stock** — only the accepted quantity is posted.
- **Enterprise isolation** — users see only their enterprise's cost centers; cross-enterprise stock is invisible in lists, reports and direct links.
- **Duplicate item names warn** for review — nothing silently merges.

---

## 2. Demo accounts

All passwords: **`aig2026`** · Company: Adama Investment Group

### Inventory cast (today's focus)

| Login | Person / Role | Sees & can do |
|---|---|---|
| `enduser.agro@aig.local` | End User — Agro | Creates own stock requests (Agro cost centers), confirms receipt |
| `storeadmin.agro@aig.local` | Main Store Administrator — Agro | Reviews requests (records budget check), approves receiving at Agro stores; scoped to Dairy/Poultry stores |
| `head.agro@aig.local` | Enterprise Head — Agro | Final approval of Agro requests; sees Agro stock only |
| `storekeeper.agro@aig.local` | Store Keeper — Agro | Receiving inspections, issues, transfers for Dairy/Poultry stores |
| `gsk@aig.local` | General Store Keeper | Approves receiving inspections (all stores) |
| `property.expert@aig.local` | Property Administration Expert | Assigns bins/barcodes/asset tags during receiving |
| `mainstore@aig.local` | Main Store Administrator (Head Office) | Main Store final approvals, issues from Main Store (scoped to Main Store) |
| `inv.admin@aig.local` | Inventory Administrator | Item groups, item master, warehouse setup, barcode/bin rules |
| `auditor@aig.local` | Internal Auditor | Read-only on all inventory transactions & approvals |

### Procurement / finance cast (for the second half of the demo)

| Login | Role |
|---|---|
| `procurement.agro@aig.local` | Procurement Officer — Agro |
| `committee1@aig.local` / `committee2@…` / `committee3@…` | Purchase Committee |
| `corporate@aig.local`, `ceo@aig.local`, `deputy@aig.local`, `finance@aig.local` | Corporate / CEO / Deputy / Finance |

> Tip: open one **incognito window per role** so you can switch without logging out.

### Where each role works (sidebar workspaces)

- End User → **AIG Inventory Requests**
- Store Keeper / Store Admin / Main Store → **AIG Store Operations**
- Property Expert → **AIG Property Administration**
- Enterprise Head → **AIG Approvals**
- Auditor / Finance → **AIG Inventory Reports & Audit**
- Inventory Administrator → **Stock** + **AIG Store Operations**

---

## 3. Item registration (with the specified user)

**Who registers items: the Inventory Administrator (`inv.admin@aig.local`)** — item master is a controlled master-data duty, not a transactional workflow; changes are audit-logged. (If AIG later wants a formal *item approval workflow*, that is a configuration decision — see §9.)

1. Log in as `inv.admin@aig.local`.
2. Sidebar → **Stock → Item** (or AIG Store Operations → Items) → **+ Add Item**.
3. Fill: **Item Code** (e.g. `AIG-DAIRY-MILKCUP`), **Item Name**, **Item Group** — choose deliberately:
   - `Consumable Stock` — normal stock items
   - `Livestock & Biological Assets` — biological assets
   - `Property & Fixed Assets` — trackable property
   - `Forms & Vouchers` — administrative forms
4. Tick **Maintain Stock** for stock items; set **Stock UOM** (Nos, Kg, Ltr…); set **Default Warehouse** in Item Defaults (company AIG).
5. Save. If a similar **item name already exists, a warning appears for review** — verify whether it is truly a new item or a duplicate; the system never merges silently.
6. Reorder levels, barcode, batch/serial/expiry are available per item where relevant.

**Classification rule for leaders:** not every register line is stock — property/fixed assets are tracked on the Asset side, forms/vouchers as non-stock items.

---

## 4. Flow A — Receiving into a store (Quality Form path)

Story: 40 bags of Dairy Feed arrive at Dairy Farm Store against delivery note `DEL-2026-114`.

1. **Store Keeper** (`storekeeper.agro@aig.local`) → **AIG Store Operations → Stock Entry → + Add**.
   - Stock Entry Type = **Material Receipt**; Target Warehouse = `Dairy Farm Store - AIG`; AIG Enterprise (Cost Center) = `Dairy Farm - AIG`.
   - Items: `AIG-INV-FEED`, qty 40, basic rate 40; **Source/Reference Document** = `DEL-2026-114`.
   - Save → click **Start Receiving** → state badge: **Pending Inspection**. *(No stock yet.)*
2. **Store Keeper** records the inspection: create the **Quality Form** (Quality Inspection: Incoming, reference = this Stock Entry, sample size, Accepted/Rejected qty, notes, attach the delivery scan) → submit it → back on the Stock Entry click **Record Inspection** → **Pending GSK Approval**.
3. **General Store Keeper** (`gsk@aig.local`) opens it → **Approve** → **Pending Property Assignment**. (Or **Reject** with reason.)
4. **Property Administration Expert** (`property.expert@aig.local`) assigns **bin location / barcode / asset tag** on the items →
   - **Assign Bins** (non-Main-Store receipts) → **Pending Posting**, or
   - **Assign Bins** into **Pending Main Store Approval** when the receipt is for Main Store.
5. **General Store Keeper** clicks **Post Receipt** (or **Main Store Administrator** `mainstore@aig.local` clicks **Final Approve & Post** for Main Store) → **Posted**.
6. **Only now** the accepted quantity is visible in stock (Stock Balance / Bin). Show the audit trail: each state change records **who** and **when**.

**Demo highlight:** between steps 1–5 the on-hand quantity does not move — proof that unapproved receipts can't leak into stock.

---

## 5. Flow B — Stock request → approval → issue → confirmation (Model 19 / Model 22)

Story: Dairy Farm asks for 20 bags of feed.

1. **End User** (`enduser.agro@aig.local`) → **AIG Inventory Requests → Stock Request (Model 19) → + Add**.
   - Material Request Type = **Material Issue**; AIG Enterprise = `Dairy Farm - AIG`; Purpose = "weekly feed"; Destination Store; needed-by date; items + quantities.
   - Save → **Submit Request** → **Pending Store Review**. *(Status shows on their list.)*
2. **Main Store Administrator** (`storeadmin.agro@aig.local`) opens it:
   - records the **Budget Check** (`Budget Checked` + note — if budget data wasn't available, say so honestly; the honest note is mandatory),
   - checks availability,
   - clicks **Approve** → **Pending Enterprise Approval**. (Approving without the budget check is blocked.)
3. **Enterprise Head — Agro** (`head.agro@aig.local`) → **Approve** → **Approved**.
   *(Try it as `head.construction@aig.local` instead: the request is invisible — enterprise isolation.)*
4. **Store Keeper** (`storekeeper.agro@aig.local`) → AIG Store Operations → **Stock Entry**, type **Material Issue**:
   - **Against Stock Request (Model 19)** = the approved request (items/quantities pull in);
   - **Issued To** = the end user; Save → click **Post Movement** → **Posted** → Model 22 printout.
   - Print: Print → **AIG Model 22 Issue Note** (request ref, issue ref, items, recipient, signature blocks).
5. **End User** confirms receipt: open their request (still visible in AIG Inventory Requests) → set **Received By / Receipt Confirmed + note** → save. Print → **AIG Receipt Confirmation** for filing.
6. Stock is now reduced (only at step 4, never earlier).

**Partial fulfilment:** issue less than approved; the request keeps its remaining quantity. **Over-issue is blocked by the system.**

---

## 6. Flow C — Transfers between stores/enterprises

1. Store Keeper → Stock Entry → type **Material Transfer**: source warehouse + target warehouse, quantities, both enterprise (cost center) fields.
2. **Post Movement** → Posted. No tax template applies to internal transfers (no VAT event) — by design.
3. In-transit / two-step transfers use Transfer type with in-transit warehouse, then a receiving entry at destination.

---

## 7. Flow D — Counts & adjustments

1. Store Keeper / Store Admin → **Stock Reconciliation**: purpose (Count/Reconciliation), items with counted qty.
2. **Reason Code is mandatory** (Stock Count Variance / Damaged / Expired / Obsolete / Quarantined / Correction / Opening Balance / Other) + free-text note.
3. Submit posts the correction; the original document and audit history are preserved. Damaged/expired stock leaves available stock with the correct reason.

---

## 8. Reports & status visibility ("when things are done and approved")

- **AIG Outstanding Stock Requests** — every request with its current state (Draft / Pending Store Review / Pending Enterprise Approval / Approved / Rejected).
- **Stock Balance / Stock Ledger** — on-hand by item/warehouse with movement history and source documents.
- **Bin / reorder views** — low-stock list.
- **AIG Inventory Reports & Audit workspace** — valuation + full approval audit for Finance/Auditor.
- Every document shows its **state badge**; the Workflow activity log under the form shows who did what, when.

---

## 9. Leader demo script (from login to "done & approved")

**Act 0 — Login & map (3 min).** Log in as `enduser.agro@aig.local`. Show the sidebar: *"each person sees only their world."*

**Act 1 — Request (Model 19) (7 min).** End User creates the Dairy Farm feed request → **Submit Request** → show status = *Pending Store Review*. Say: *"stock is not touched yet — this is only a request."*

**Act 2 — Store review with honest budget check (5 min).** Switch to `storeadmin.agro@aig.local`. Try **Approve without the budget check** → blocked (wow moment). Record the check → **Approve** → *Pending Enterprise Approval*.

**Act 3 — Enterprise Head approval (4 min).** `head.agro@aig.local` → **Approve** → **Approved**. Optional wow: log in as `head.construction@aig.local` and show the Agro request doesn't exist for them.

**Act 4 — Issue + Model 22 (6 min).** `storekeeper.agro@aig.local` → Stock Entry (Material Issue) against the request → **Post Movement** → print **Model 22 Issue Note**. Show Stock Balance before/after (500 → 480 bags).

**Act 5 — Receipt confirmation closes the loop (3 min).** `enduser.agro@aig.local` → request → **Receipt Confirmed** → print **AIG Receipt Confirmation**.

**Act 6 — Receiving with Quality Gate (8 min).** As the Store Keeper, start a 40-bag receipt → walk Start Receiving → Quality Form → GSK approve → Property bins → Post. Show the quantity **only moves at the very end**.

**Act 7 — Guardrails recap (5 min).** Quick hits: over-issue blocked · raw submit blocked · duplicate item name warning (create an item as `inv.admin@aig.local` named "AIG Demo Dairy Feed" → warning appears).

**Act 8 — Reports & audit (4 min).** Outstanding Stock Requests (all states visible), Stock Ledger, auditor's read-only view.

**Act 9 — (If time) Procurement pipeline.** PO approval tiers and the 4-signature payment chain, per the Procurement demo guide.

**Reset between rehearsals:** re-run `scripts/93_seed_inventory_demo.py` (idempotent — skips stock that already exists; cancel+delete the demo Stock Entries/Material Requests to replay from scratch). All scripts run via `run_script.sh` like today.

---

## 10. Open decisions for AIG (tracked, not blocking the demo)

1. Formal **item-approval workflow** (currently: Inventory Administrator registers, duplicate-warning reviews).
2. Approval **thresholds** for corporate/CEO routing on inventory actions (configurable; none hardcoded).
3. Authoritative **warehouse↔enterprise** mapping confirmation (19 warehouses live).
4. **Barcode/asset-tag** numbering rules for Property Administration.
5. Budget data source the Main Store Administrator should check (currently an honest manual note).
6. Opening-balance valuation policy for the full legacy migration (staging/validation path exists; workbooks pending).

--- END OF MANUAL ---
