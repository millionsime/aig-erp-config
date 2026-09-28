import frappe

DOCS = [("Purchase Order", "PUR-ORD-2026-00005"),
        ("Purchase Order", "PUR-ORD-2026-00006"),
        ("Payment Entry", "ACC-PAY-2026-00003")]

USERS = {
    "AIG Procurement Officer": "procurement.agro@aig.local",
    "AIG Purchase Committee": "committee1@aig.local",
    "AIG Enterprise Head": "head.agro@aig.local",
    "AIG Corporate": "corporate@aig.local",
    "AIG CEO": "ceo@aig.local",
    "AIG Deputy": "deputy@aig.local",
    "AIG Finance": "finance@aig.local",
}


def link_targets(dt, dn):
    doc = frappe.get_doc(dt, dn)
    meta = frappe.get_meta(dt)
    out = set()
    for df in meta.fields:
        if df.fieldtype == "Link" and df.options:
            v = doc.get(df.fieldname)
            if v:
                out.add((df.options, v))
        if df.fieldtype == "Table" and df.options:
            cmeta = frappe.get_meta(df.options)
            for row in (doc.get(df.fieldname) or []):
                for cdf in cmeta.fields:
                    if cdf.fieldtype == "Link" and cdf.options:
                        cv = row.get(cdf.fieldname)
                        if cv:
                            out.add((cdf.options, cv))
    return out


# full role list for one approver, to see the baseline
print("=== FULL roles of committee1 ===")
print(sorted(frappe.get_roles("committee1@aig.local")))

# which of the linked doctypes have Custom DocPerm overrides
all_links = set()
for dt, dn in DOCS:
    all_links |= link_targets(dt, dn)
linked_doctypes = sorted({d for d, v in all_links})
print("\n=== linked doctypes on the demo docs ===")
for d in linked_doctypes:
    print(f"  {d:28s} custom_docperm_rows={frappe.db.count('Custom DocPerm', {'parent': d})}")

print("\n=== per-approver READ failures on linked docs ===")
for role, user in USERS.items():
    frappe.set_user(user)
    fails = []
    for d, v in sorted(all_links):
        try:
            if not frappe.has_permission(d, "read", doc=v, throw=False):
                fails.append(f"{d}:{v}")
        except Exception as e:
            fails.append(f"{d}:{v} ERR {type(e).__name__}")
    frappe.set_user("Administrator")
    tag = "OK" if not fails else "MISSING"
    print(f"  [{tag}] {role:26s} ({user})")
    for f in fails:
        print(f"        - {f}")

print("\nLINKCHECK_DONE")
