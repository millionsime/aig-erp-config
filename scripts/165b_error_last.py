# 165b_error_last.py -- READ-ONLY: the newest Error Log entry in full.
import frappe


def log(*a):
    print(*a, flush=True)


rows = frappe.get_all("Error Log", fields=["creation", "method", "error"],
                      order_by="creation desc", limit_page_length=1)
for r in rows:
    log(f"=== {r.creation} | method={r.method!r} ===")
    log((r.error or "")[-2500:])
log("DONE 165b")
