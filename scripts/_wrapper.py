import sys
import frappe

# Bootstrap a Frappe request-less context so standalone AIG setup scripts run
# in ONE consistent namespace (avoids IPython console fragmentation).
frappe.init(site="frontend", sites_path="sites")
frappe.connect()
frappe.set_user("Administrator")

code = sys.stdin.read()
try:
    exec(compile(code, "<aig-script>", "exec"), globals())
    frappe.db.commit()
    print("\n@@ WRAPPER_OK committed")
except Exception:
    frappe.db.rollback()
    import traceback
    traceback.print_exc()
    print("\n@@ WRAPPER_FAILED rolled back")
finally:
    frappe.destroy()
