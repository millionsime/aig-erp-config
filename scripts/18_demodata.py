# 18 - Add a small, clean set of LIVE demo data so every workflow can be tested
# by hand in the UI:
#   * 3 Draft Purchase Orders, one per policy tier (Direct / Proforma / Bulky)
#   * 1 ready-to-run Payment chain: pre-Approved PO -> PR (Model 19) -> PI -> Draft PE
#   * 1 extra officer (procurement.construction) so the Bulky/Construction tier can
#     be submitted by a properly cost-center-scoped Procurement Officer.
# Idempotent: if the marker Payment Entry already exists, it reports and exits.
import frappe
from frappe.model.workflow import apply_workflow

COMPANY = "Adama Investment Group"
POST = "2026-09-24"
MARKER = "AIGDEMO-LIVE-400K"

COGS = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Cost of Goods Sold"})
CREDITORS = frappe.db.get_value("Account", {"company": COMPANY, "account_name": ["like", "Creditors%"]})
BANK = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Commercial Bank of Ethiopia"})
CC = {n: frappe.db.get_value("Cost Center", {"company": COMPANY, "cost_center_name": n})
      for n in ["Dairy Farm", "Construction"]}


def as_user(u):
    frappe.set_user(u)


def admin():
    frappe.set_user("Administrator")


def make_po(user, supplier, item, qty, rate, cc_name):
    as_user(user)
    po = frappe.get_doc({
        "doctype": "Purchase Order", "company": COMPANY, "supplier": supplier,
        "transaction_date": POST, "schedule_date": POST,
        "aig_cost_center": CC[cc_name],
        "items": [{"item_code": item, "qty": qty, "rate": rate, "schedule_date": POST,
                   "cost_center": CC[cc_name], "expense_account": COGS}],
    })
    po.insert(ignore_permissions=True)
    admin()
    return po.name


def ensure_officer():
    officer = "procurement.construction@aig.local"
    as_user("Administrator")
    if not frappe.db.exists("User", officer):
        u = frappe.get_doc({
            "doctype": "User", "email": officer, "first_name": "Procurement Officer - Construction",
            "enabled": 1, "user_type": "System User", "new_password": "aig2026",
            "send_welcome_email": 0, "language": "en",
            "roles": [{"role": "AIG Procurement Officer"}],
        })
        u.flags.ignore_permissions = True
        u.insert(ignore_permissions=True)
        print("CREATED user", officer, "password=aig2026")
    else:
        # repair a partially-created user: ensure enabled, role and password
        u = frappe.get_doc("User", officer)
        u.flags.ignore_permissions = True
        u.enabled = 1
        u.new_password = "aig2026"
        if not any(r.role == "AIG Procurement Officer" for r in u.roles):
            u.append("roles", {"role": "AIG Procurement Officer"})
        u.save(ignore_permissions=True)
        print("REPAIRED user", officer, "password=aig2026")
    admin()
    # mirror head.construction's Cost Center User Permissions (idempotent)
    for cc in frappe.get_all("User Permission",
                             filters={"user": "head.construction@aig.local", "allow": "Cost Center"},
                             pluck="for_value"):
        if not frappe.db.exists("User Permission",
                                {"user": officer, "allow": "Cost Center", "for_value": cc}):
            frappe.get_doc({
                "doctype": "User Permission", "user": officer, "allow": "Cost Center",
                "for_value": cc, "apply_to_all_doctypes": 1,
            }).insert(ignore_permissions=True)
            print("  UP", officer, "->", cc)
    frappe.db.commit()
    return officer


def build():
    officer = ensure_officer()

    # 3 Draft POs (one per tier) --------------------------------------
    po_direct = make_po("procurement.agro@aig.local", "Ethio Dairy Supplies PLC",
                        "AIG-DAIRY-FEED", 1, 15000, "Dairy Farm")
    po_proforma = make_po("procurement.agro@aig.local", "Horizon Agro Inputs PLC",
                          "AIG-DAIRY-FEED", 1, 250000, "Dairy Farm")
    po_bulky = make_po(officer, "Blue Nile Trade PLC",
                       "AIG-STEEL", 1, 900000, "Construction")
    print("DRAFT PO Direct   (15k)  :", po_direct)
    print("DRAFT PO Proforma (250k) :", po_proforma)
    print("DRAFT PO Bulky    (900k) :", po_bulky)

    # Ready payment chain (400k) --------------------------------------
    po_pay = make_po("procurement.agro@aig.local", "Ethio Dairy Supplies PLC",
                     "AIG-PACK", 1, 400000, "Dairy Farm")
    as_user("procurement.agro@aig.local")
    apply_workflow(frappe.get_doc("Purchase Order", po_pay), "Submit for Committee Review")
    admin()
    as_user("committee1@aig.local")
    apply_workflow(frappe.get_doc("Purchase Order", po_pay), "Approve")   # -> Enterprise Head (<=750k)
    admin()
    as_user("head.agro@aig.local")
    apply_workflow(frappe.get_doc("Purchase Order", po_pay), "Approve")   # -> Approved
    admin()
    print("PAY-CHAIN PO Approved (400k):", po_pay,
          "->", frappe.db.get_value("Purchase Order", po_pay, "workflow_state"))

    as_user("procurement.agro@aig.local")
    pr = frappe.get_doc({
        "doctype": "Purchase Receipt", "company": COMPANY, "supplier": "Ethio Dairy Supplies PLC",
        "posting_date": POST, "set_posting_time": 1, "aig_cost_center": CC["Dairy Farm"],
        "items": [{"item_code": "AIG-PACK", "qty": 1, "rate": 400000, "cost_center": CC["Dairy Farm"],
                   "expense_account": COGS, "purchase_order": po_pay}],
    })
    pr.insert(ignore_permissions=True)
    pr.submit()
    admin()

    as_user("finance@aig.local")
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": "Ethio Dairy Supplies PLC",
        "posting_date": POST, "update_stock": 0, "aig_cost_center": CC["Dairy Farm"],
        "items": [{"item_code": "AIG-PACK", "qty": 1, "rate": 400000, "cost_center": CC["Dairy Farm"],
                   "expense_account": COGS, "purchase_order": po_pay, "purchase_receipt": pr.name}],
    })
    pi.insert(ignore_permissions=True)
    pi.submit()
    admin()
    print("PAY-CHAIN PR (Model 19):", pr.name, " PI:", pi.name)

    as_user("finance@aig.local")
    pe = frappe.get_doc({
        "doctype": "Payment Entry", "company": COMPANY, "payment_type": "Pay",
        "party_type": "Supplier", "party": "Ethio Dairy Supplies PLC",
        "paid_from": BANK, "paid_to": CREDITORS,
        "reference_no": MARKER, "reference_date": POST,
        "paid_amount": 400000, "received_amount": 400000,
        "references": [{"reference_doctype": "Purchase Invoice", "reference_name": pi.name,
                        "allocated_amount": 400000}],
    })
    pe.insert(ignore_permissions=True)
    admin()
    print("DRAFT Payment Entry (400k):", pe.name,
          "->", frappe.db.get_value("Payment Entry", pe.name, "workflow_state"))

    frappe.db.commit()
    print("\n=== SUMMARY OF NEW DEMO DATA ===")
    print(f"  Draft PO  Direct   15k  Dairy Farm    : {po_direct}")
    print(f"  Draft PO  Proforma 250k Dairy Farm    : {po_proforma}")
    print(f"  Draft PO  Bulky    900k Construction  : {po_bulky}")
    print(f"  Approved PO        400k Dairy Farm    : {po_pay}")
    print(f"  Purchase Receipt (Model 19)           : {pr.name}")
    print(f"  Purchase Invoice                      : {pi.name}")
    print(f"  Draft Payment Entry 400k              : {pe.name}")
    print(f"  New user                              : {officer}")
    print("DEMODATA_DONE")


if frappe.get_all("Payment Entry", filters={"reference_no": MARKER}, pluck="name"):
    print("Demo data already present (marker PE). Nothing to do. DEMODATA_SKIPPED")
else:
    build()
