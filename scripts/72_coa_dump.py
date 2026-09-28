# Full live CoA dump for the review doc (read-only).
rows = frappe.get_all("Account",
                      filters={"company": "Adama Investment Group"},
                      fields=["name", "account_name", "parent_account", "is_group",
                              "account_type", "root_type", "account_number"],
                      order_by="lft")
for r in rows:
    indent = "  " * max(0, r.name.count("/") - 0)
    print(f"{'[G]' if r.is_group else '   '} {r.name} | type={r.account_type or '-'} | num={r.account_number or '-'}")
print("total:", len(rows))
print("DONE")
