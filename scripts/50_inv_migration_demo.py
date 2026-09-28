# AIG config - step 50: migration staging DEMO + reconciliation (config layer).
# Proves the staging -> validation -> reconciliation path end-to-end WITHOUT the real
# legacy workbooks (which were not supplied). Creates ONE clearly-marked reversible
# demo batch with synthetic rows that cover every validation branch, saves it (which
# runs the "AIG - Migration Batch Validation" server script), then prints the review
# report + reconciliation totals. NO stock is posted; nothing is imported.
# FLAG: replace this demo with the real .xlsx/.xlsb loader described in INVENTORY_GUIDE.
import frappe
import traceback

ABBR = "AIG"
DEMO_WORKBOOK = "AIG-DEMO-STOCKCARD.xlsx"
DEMO_SHEET = "Dairy Store Card"
DAIRY_WH = f"Dairy Farm Store - {ABBR}"
DAIRY_CC = f"Dairy Farm - {ABBR}"
ITEM = "AIG-INV-FEED"

# synthetic staged rows: (record_type, item_code, uom, qty, rate, raw_name, raw_qty,
#                         raw_date, raw_store, warehouse, cost_center)
DEMO_ROWS = [
    # A: the ONE clean, valid opening balance (Excel serial date 45000 ~ 2023-03-15)
    ("Opening Balance", ITEM, "Nos", 50, 10, "Dairy Feed 50kg", "50", "45000",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
    # B + C: duplicate-candidate pair (same raw item name) -> Warning, flagged, not merged
    ("Historical Movement", None, "Nos", 5, 0, "Legacy Item X", "5", "2023-01-10",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
    ("Historical Movement", None, "Nos", 7, 0, "Legacy Item X", "7", "2023-01-11",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
    # D: opening balance missing the mapped item -> Error
    ("Opening Balance", None, "Nos", 10, 0, "Unmapped Thing", "10", "2023-01-05",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
    # E: invalid / ambiguous date -> Error
    ("Historical Movement", None, "Nos", 5, 0, "Feed issue", "5", "not-a-date",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
    # F: form/voucher classification + unmapped store -> Warning
    ("Form / Voucher", None, None, None, None, "Model 22 voucher book", "", "",
     "Some Legacy Store", None, None),
    # G: negative source quantity -> Warning (never auto-corrected)
    ("Historical Movement", None, "Nos", -5, 0, "Feed correction", "-5", "2023-02-01",
     "Dairy Farm Store", DAIRY_WH, DAIRY_CC),
]


def build_rows():
    out = []
    for i, (rt, code, uom, qty, rate, rname, rqty, rdate, rstore, wh, cc) in enumerate(DEMO_ROWS):
        out.append({
            "source_workbook": DEMO_WORKBOOK, "sheet_name": DEMO_SHEET,
            "source_row_no": i + 2, "source_ref": f"{DEMO_SHEET}!R{i + 2}",
            "raw_item_code": code or "", "raw_item_name": rname, "raw_qty": rqty,
            "raw_uom": uom or "", "raw_rate": ("" if rate is None else str(rate)),
            "raw_date": rdate, "raw_store": rstore, "raw_enterprise": "Agro",
            "record_type": rt, "item_code": code, "uom": uom,
            "qty": qty, "valuation_rate": rate, "warehouse": wh, "cost_center": cc,
        })
    return out


print("=== staging demo batch (synthetic, reversible) ===")
try:
    existing = frappe.db.get_value("AIG Stock Migration Batch",
                                   {"source_workbook": DEMO_WORKBOOK}, "name")
    if existing:
        frappe.delete_doc("AIG Stock Migration Batch", existing,
                          ignore_permissions=True, force=True)
        frappe.db.commit()
        print("removed prior demo batch:", existing)

    batch = frappe.get_doc({
        "doctype": "AIG Stock Migration Batch",
        "source_workbook": DEMO_WORKBOOK, "sheet_name": DEMO_SHEET,
        "enterprise": DAIRY_CC, "effective_date": frappe.utils.today(),
        "valuation_method": "Moving Average", "status": "Staged",
        "separate_history": 1,
        "rows": build_rows(),
    })
    batch.flags.ignore_permissions = True
    batch.insert(ignore_permissions=True)   # triggers the validation server script
    frappe.db.commit()
    batch.reload()
    print("created batch:", batch.name)

    print("\n=== validation review report ===")
    print(f"total={batch.total_rows} valid={batch.valid_rows} "
          f"warning={batch.warning_rows} error={batch.error_rows} "
          f"duplicate={batch.duplicate_rows} status={batch.status}")
    for r in batch.rows:
        print(f"  row {r.source_row_no} [{r.record_type}] {r.validation_status}"
              f"{' DUP' if r.is_duplicate_candidate else ''}"
              f"{' SERIAL->' + str(r.date_converted) if r.date_is_excel_serial else ''}")
        if r.validation_messages:
            for line in str(r.validation_messages).split("\n"):
                if line.strip():
                    print(f"        - {line}")

    # Excel serial conversion assertion
    rowA = batch.rows[0]
    conv_ok = bool(rowA.date_is_excel_serial) and rowA.date_converted and \
        frappe.utils.getdate(rowA.date_converted).year > 1990
    print("\nExcel serial 45000 -> ", rowA.date_converted, "converted_ok=", conv_ok)

    # reconciliation by store and by item (valid opening balances only)
    print("\n=== reconciliation (Valid 'Opening Balance' rows) ===")
    by_store = {}
    by_item = {}
    for r in batch.rows:
        if r.record_type == "Opening Balance" and r.validation_status == "Valid":
            by_store[r.warehouse or "(unmapped)"] = (by_store.get(r.warehouse or "(unmapped)") or 0) + (r.qty or 0)
            by_item[r.item_code or "(unmapped)"] = (by_item.get(r.item_code or "(unmapped)") or 0) + (r.qty or 0)
    print("  by store:", by_store)
    print("  by item :", by_item)

    print("\nMIGRATION_DEMO_DONE")
except Exception:
    print("EXCEPTION:")
    print(traceback.format_exc())


def run():
    frappe.db.commit()
    return "migration demo staged"
