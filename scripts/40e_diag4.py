# AIG config - step 40e: inspect Frappe user-permission matching source.
import frappe
import inspect

try:
    from frappe.permissions import DocumentPermission
    print("DocumentPermission module:", inspect.getfile(DocumentPermission))
    src = inspect.getsource(DocumentPermission)
    # print only the parts mentioning user permission
    for chunk in src.split("\n\n"):
        if "user_permission" in chunk.lower() or "get_user_permission" in chunk.lower():
            print("----- chunk -----")
            print(chunk)
except Exception:
    import traceback
    print(traceback.format_exc())

print("\n\n=== has_permission signature ===")
print(inspect.signature(frappe.has_permission))
print("DONE")
