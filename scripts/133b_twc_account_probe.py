# 133b_twc_account_probe.py -- v16 moved/renamed the Tax Withholding posting
# account (rate rows have no account column). Find where it lives now and how
# Payment Entry resolves it. READ-ONLY.

import frappe


def log(*a):
    print(*a, flush=True)


log("1) Tax Withholding Category meta fields")
for f in frappe.get_meta("Tax Withholding Category").fields:
    log(f"  {f.fieldname} ({f.fieldtype}) label={f.label!r}")

log("")
log("2) both AIG TWC category docs (full)")
for cat in ["AIG 7.5% VAT Withholding", "AIG 3% Withholding Tax"]:
    d = frappe.get_doc("Tax Withholding Category", cat)
    log(f"--- {cat} ---")
    for k, v in d.as_dict().items():
        if k not in ("rates", "accounts") and v not in (None, "", 0):
            log(f"  {k} = {v!r}")
    for r in d.get("rates") or []:
        log(f"  rate row: {r.as_dict()}")
    for a in d.get("accounts") or []:
        log(f"  account row: {a.as_dict()}")

log("")
log("3) erpnext source: how PE resolves the withholding account")
