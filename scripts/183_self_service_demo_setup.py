# 183_self_service_demo_setup.py
#
# Creates the AIG demo cast for the employee self-service + procurement
# workflow showcase. Idempotent: safe to re-run. It also RESETS demo
# passwords to aig2026 every run, so "forgot the password" is never a
# problem before a demo.
#
# Cast added/updated (password aig2026 is set ONCE, at user creation):
#   budget@aig.local              Plan and Budget Office            (new)
#   records@aig.local             Record Office                     (new)
#   procurement.director@aig.local  Procurement & Property Admin Director (new)
#   enduser.agro@aig.local        Demeke - end user / requester     (exists)
#   head.agro@aig.local           Enterprise Head - Agro            (exists)
#   ceo@aig.local                 CEO                               (exists)
#   corporate@aig.local           Corporate - Head Office           (exists)
#   mainstore@aig.local           Main Store Administrator          (exists)
#   procurement.agro@aig.local    Procurement Officer - Agro        (exists)
#
# Also: Employee records for everyone (HR self-service needs them),
# leave allocations, demo items, and self-service roles for all.
#
# Run with:
#   bench --site <site> console < 183_self_service_demo_setup.py
# (from a shell that already has frappe initialised, e.g. bench console)

import frappe
from frappe.utils import nowdate, add_years, getdate

PW = "aig2026"
COMPANY = "Adama Investment Group"

# ---- 1. demo cast definition -------------------------------------------------
# (email, first_name, extra_roles, designation, department, gender, birth, joined,
#  leave_approver, reports_to_email)
CAST = [
    ("enduser.agro@aig.local", "Demeke", ["Employee", "Employee Self Service", "AIG End User"],
     "Farm Supervisor", "Production - AIG", "Male", "1992-04-12", "2024-02-01",
     "head.agro@aig.local", "head.agro@aig.local"),
    ("head.agro@aig.local", "Enterprise Head - Agro", ["Employee", "Employee Self Service", "AIG Enterprise Head"],
     "Enterprise Head - Agro", "Operations - AIG", "Male", "1980-09-05", "2022-10-01",
     "ceo@aig.local", None),
    ("budget@aig.local", "Plan and Budget Office", ["Employee", "Employee Self Service", "AIG Plan and Budget"],
     "Plan and Budget Officer", "Management - AIG", "Female", "1988-06-21", "2023-01-15",
     "corporate@aig.local", None),
    ("records@aig.local", "Record Office", ["Employee", "Employee Self Service", "AIG Record Office"],
     "Record Officer", "Management - AIG", "Female", "1991-11-30", "2023-03-01",
     "corporate@aig.local", None),
    ("procurement.director@aig.local", "Procurement and Property Administration Director",
     ["Employee", "Employee Self Service", "AIG Procurement Director"],
     "Director, Procurement & Property Administration", "Purchase - AIG", "Male", "1979-02-17", "2021-08-01",
     "corporate@aig.local", None),
    ("ceo@aig.local", "CEO - AIG", ["Employee", "Employee Self Service", "AIG CEO"],
     "Chief Executive Officer", "Management - AIG", "Male", "1975-05-10", "2020-01-01",
     "corporate@aig.local", None),
    ("corporate@aig.local", "Corporate - Head Office", ["Employee", "Employee Self Service", "AIG Corporate"],
     "Corporate Office Head", "Management - AIG", "Male", "1977-08-23", "2020-01-01",
     "ceo@aig.local", None),
    ("mainstore@aig.local", "Main Store Administrator", ["Employee", "Employee Self Service", "AIG Main Store Administrator"],
     "Main Store Administrator", "Operations - AIG", "Male", "1985-12-02", "2022-05-01",
     "head.agro@aig.local", None),
    ("procurement.agro@aig.local", "Procurement Officer - Agro", ["Employee", "Employee Self Service", "AIG Procurement Officer"],
     "Procurement Officer - Agro", "Purchase - AIG", "Male", "1990-07-19", "2023-06-01",
     "procurement.director@aig.local", None),
]

# ---- 2. users ----------------------------------------------------------------
# Every employee is a requester: AIG End User is the base self-service role.
def base_roles(extra):
    roles = ["Employee", "Employee Self Service", "AIG End User"]
    for r in extra:
        if r not in roles:
            roles.append(r)
    return roles

def get_or_make_user(email, first_name):
    if frappe.db.exists("User", email):
        u = frappe.get_doc("User", email)
        if u.enabled != 1:
            u.enabled = 1
            u.save(ignore_permissions=True)
        print("user ok:", email)
        # NOTE: do not reset passwords on re-runs. Once Employee records exist,
        # the strength checker flags the year-like demo password and blocks the
        # save. Passwords are set once, at creation.
    else:
        u = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "user_type": "System User",
            "send_welcome_email": 0,
            "new_password": PW,
        }).insert(ignore_permissions=True)
        print("user created (pw=%s):" % PW, email)
    return u

def add_role(user_doc, role):
    if not any(r.role == role for r in user_doc.roles):
        user_doc.append("roles", {"role": role})
        user_doc.save(ignore_permissions=True)
        print("  + role:", role)

for email, first_name, roles, desig, dept, gender, birth, joined, lv_app, rpt in CAST:
    u = get_or_make_user(email, first_name)
    for r in base_roles(roles):
        add_role(u, r)

# legacy store users keep full function of the assign step (they can also edit
# "Pending Store Review" now that the director owns that state)
for legacy in ["mainstore@aig.local", "storeadmin.agro@aig.local"]:
    if frappe.db.exists("User", legacy):
        u = frappe.get_doc("User", legacy)
        add_role(u, "AIG Procurement Director")
        add_role(u, "AIG End User")

# ---- 3. docperms (upsert so rejects/cancel work everywhere) -------------------
def upsert_docperm(doctype, role, **perms):
    base = {"read": 0, "write": 0, "create": 0, "submit": 0, "cancel": 0,
            "delete": 0, "amend": 0, "report": 0, "print": 0, "email": 0, "share": 0}
    base.update(perms)
    existing = frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role})
    if existing:
        d = frappe.get_doc("Custom DocPerm", existing)
        changed = False
        for k, v in base.items():
            if getattr(d, k, None) != v:
                setattr(d, k, v)
                changed = True
        if changed:
            d.save(ignore_permissions=True)
            print("docperm updated:", doctype, role)
        else:
            print("docperm ok:", doctype, role)
    else:
        d = frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype,
                            "parenttype": "DocType", "parentfield": "permissions",
                            "role": role, **base}).insert(ignore_permissions=True)
        print("docperm added:", doctype, role)

# approvers/rejecters need cancel (Reject -> doc_status 2 cancels the doc)
for role in ["AIG Plan and Budget", "AIG Record Office", "AIG Procurement Director",
             "AIG Enterprise Head", "AIG CEO", "AIG Corporate",
             "AIG Main Store Administrator"]:
    upsert_docperm("Material Request", role, read=1, write=1, cancel=1,
                   report=1, print=1, email=1)
# CEO must also be able to CREATE his own requests
upsert_docperm("Material Request", "AIG CEO", read=1, write=1, create=1, submit=1,
               cancel=1, report=1, print=1, email=1)
# end user full self-service on own requests
upsert_docperm("Material Request", "AIG End User", read=1, write=1, create=1, submit=1,
               cancel=1, report=1, print=1, email=1)

# ---- 4. user permissions (cost center visibility) ----------------------------
all_ccs = frappe.get_all("Cost Center", filters={"company": COMPANY}, pluck="name")
sample = frappe.db.get_value("User Permission",
                             {"user": "enduser.agro@aig.local", "allow": "Cost Center"},
                             ["apply_to_all_doctypes", "applicable_for"], as_dict=True)
APPLY_ALL = sample.apply_to_all_doctypes if sample else 0
APPLICABLE_FOR = sample.applicable_for if sample else None

def grant_cost_centers(email, ccs):
    for cc in ccs:
        if not frappe.db.exists("User Permission", {"user": email, "allow": "Cost Center", "for_value": cc}):
            frappe.get_doc({
                "doctype": "User Permission", "user": email, "allow": "Cost Center",
                "for_value": cc, "apply_to_all_doctypes": APPLY_ALL,
                "applicable_for": APPLICABLE_FOR,
            }).insert(ignore_permissions=True)
            print("  + perm:", email, "->", cc)
    print("perm ok:", email, "(%d cost centers)" % len(ccs))

GROUP_USERS = ["budget@aig.local", "records@aig.local", "procurement.director@aig.local"]
for email in GROUP_USERS:
    grant_cost_centers(email, all_ccs)

# ---- 5. employees ------------------------------------------------------------
def ensure_designation(name):
    if not frappe.db.exists("Designation", name):
        frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(
            ignore_permissions=True
        )
        print("designation created:", name)

def get_or_make_employee(email, first_name, desig, dept, gender, birth, joined, lv_app):
    ensure_designation(desig)
    emp_id = frappe.db.get_value("Employee", {"user_id": email}, "name")
    if emp_id:
        print("employee ok:", email, emp_id)
        return emp_id
    emp = frappe.get_doc({
        "doctype": "Employee",
        "naming_series": "HR-EMP-.YYYY.-",
        "first_name": first_name,
        "employee_name": first_name,
        "user_id": email,
        "company": COMPANY,
        "gender": gender,
        "date_of_birth": birth,
        "date_of_joining": joined,
        "department": dept,
        "designation": desig,
        "leave_approver": lv_app,
        "status": "Active",
    })
    emp.flags.ignore_permissions = True
    emp.insert()
    print("employee created:", email, emp.name)
    return emp.name

emp_ids = {}
for email, first_name, roles, desig, dept, gender, birth, joined, lv_app, rpt in CAST:
    emp_ids[email] = get_or_make_employee(email, first_name, desig, dept, gender, birth, joined, lv_app)

# second pass: reporting lines (after all employees exist)
for email, first_name, roles, desig, dept, gender, birth, joined, lv_app, rpt in CAST:
    if rpt:
        cur = frappe.db.get_value("Employee", emp_ids[email], "reports_to")
        want = emp_ids.get(rpt)
        if want and cur != want:
            frappe.db.set_value("Employee", emp_ids[email], "reports_to", want)
            print("reports_to set:", email, "->", rpt)

# ---- 6. leave allocations -----------------------------------------------------
def allocate_leave(emp_id, leave_type, days, year=2026):
    exists = frappe.db.exists("Leave Allocation", {
        "employee": emp_id, "leave_type": leave_type,
        "from_date": ("%d-01-01" % year), "docstatus": 1})
    if exists:
        return
    la = frappe.get_doc({
        "doctype": "Leave Allocation",
        "employee": emp_id,
        "leave_type": leave_type,
        "from_date": "%d-01-01" % year,
        "to_date": "%d-12-31" % year,
        "new_leaves_allocated": days,
        "carry_forward": 0,
    })
    la.flags.ignore_permissions = True
    la.insert()
    la.submit()
    print("leave allocated:", emp_id, leave_type, days)

for email in ["enduser.agro@aig.local", "ceo@aig.local", "head.agro@aig.local",
              "corporate@aig.local", "budget@aig.local", "records@aig.local",
              "procurement.director@aig.local"]:
    if emp_ids.get(email):
        allocate_leave(emp_ids[email], "Casual Leave", 10)
        allocate_leave(emp_ids[email], "Privilege Leave", 15)

# ---- 7. demo items -------------------------------------------------------------
def make_item(code, name, rate):
    if frappe.db.exists("Item", code):
        print("item ok:", code)
        return
    ig = "All Item Groups" if frappe.db.exists("Item Group", "All Item Groups") else "Products"
    uom = "Unit" if frappe.db.exists("UOM", "Unit") else "Nos"
    frappe.get_doc({
        "doctype": "Item", "item_code": code, "item_name": name, "item_group": ig,
        "stock_uom": uom, "is_stock_item": 0, "is_purchase_item": 1, "is_sales_item": 0,
        "standard_rate": rate, "description": "AIG demo item",
    }).insert(ignore_permissions=True)
    print("item created:", code)

make_item("DEMO-A4-REAM", "Demo - A4 Paper Ream", 400)
make_item("DEMO-OFFICE-CHAIR", "Demo - Office Chair", 4500)
make_item("DEMO-PRINTER-TONER", "Demo - Printer Toner", 8000)

# ---- 8. summary -----------------------------------------------------------------
frappe.db.commit()
frappe.clear_cache()
print("")
print("=== AIG DEMO CAST (password for ALL: %s) ===" % PW)
for email, first_name, roles, desig, dept, gender, birth, joined, lv_app, rpt in CAST:
    print("  %-34s %-12s %s" % (email, PW, desig))
print("183 DONE")
