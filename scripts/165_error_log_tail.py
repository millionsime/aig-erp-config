# 165_error_log_tail.py -- READ-ONLY: latest Error Log entries (the 500's
# real traceback lands here).
import frappe


def log(*a):
    print(*a, flush=True)


rows = frappe.get_all("Error Log",
                      fields=["creation", "method", "error"],
                      order_by="creation desc", limit_page_length=3)
for r in rows:
    log(f"=== {r.creation} method={r.method} ===")
    txt = r.error or ""
    log(txt[-1800:])
    log("")
log("DONE 165")
