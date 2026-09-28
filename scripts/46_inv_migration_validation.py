# AIG config - step 46: migration staging validation Server Script (config layer).
# Attaches to the PARENT "AIG Stock Migration Batch" (Before Save) so it reliably
# fires and can validate every staged row in one pass, then recompute reconciliation
# counters. RestrictedPython-safe (no underscore-prefixed names). Honors the brief:
# convert Excel serial dates, flag invalid/ambiguous dates, missing codes, invalid
# quantities, unmapped stores/units, missing valuation, and duplicate candidates -
# WITHOUT silently merging, discarding, or "correcting" source values.
import frappe
import traceback

LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def set_script(name, reference_doctype, doctype_event, script):
    if frappe.db.exists("Server Script", name):
        ss = frappe.get_doc("Server Script", name)
        if ss.script != script or ss.disabled or ss.doctype_event != doctype_event:
            ss.script = script
            ss.disabled = 0
            ss.doctype_event = doctype_event
            ss.reference_doctype = reference_doctype
            ss.script_type = "DocType Event"
            ss.flags.ignore_permissions = True
            ss.save(ignore_permissions=True)
            log("UPDATE", f"Server Script {name}")
        else:
            log("EXISTS", f"Server Script {name}")
        return name
    doc = frappe.get_doc({
        "doctype": "Server Script", "name": name, "script_type": "DocType Event",
        "reference_doctype": reference_doctype, "doctype_event": doctype_event,
        "script": script, "disabled": 0,
    })
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"Server Script {name}")
    except Exception:
        print(f"!! FAILED {name}")
        print(traceback.format_exc())
    return name


VALIDATION = """# AIG migration staging validation - runs before the batch is saved.
rows = doc.rows or []
doc.total_rows = len(rows)
valid = 0
warn = 0
err = 0
dup = 0

# frequency maps for within-batch duplicate detection (never auto-merge)
name_freq = {}
code_freq = {}
for r in rows:
    nm = (r.raw_item_name or "").strip().lower()
    cd = (r.item_code or "").strip()
    if nm:
        name_freq[nm] = name_freq.get(nm, 0) + 1
    if cd:
        code_freq[cd] = code_freq.get(cd, 0) + 1

EXCEL_EPOCH = frappe.utils.getdate("1899-12-30")

for r in rows:
    msgs = []
    status = "Valid"

    # ---- date: Excel serial vs real date vs invalid/ambiguous
    raw = (r.raw_date or "").strip()
    r.date_is_excel_serial = 0
    if raw:
        serial = None
        try:
            num = float(raw)
            if num == int(num) and 1 <= num <= 60000:
                serial = int(num)
        except Exception:
            serial = None
        if serial:
            r.date_is_excel_serial = 1
            conv = frappe.utils.add_days(EXCEL_EPOCH, serial)
            r.date_converted = conv
            if not r.posting_date:
                r.posting_date = conv
        else:
            try:
                conv = frappe.utils.getdate(raw)
                r.date_converted = conv
                if not r.posting_date:
                    r.posting_date = conv
            except Exception:
                msgs.append("Raw date '" + raw + "' is not a valid date or Excel serial - review.")
                status = "Error"

    # ---- quantity
    qraw = (r.raw_qty or "").strip()
    if qraw:
        try:
            q = float(qraw.replace(",", ""))
            if q < 0:
                msgs.append("Negative source quantity - review (not auto-corrected).")
                if status == "Valid":
                    status = "Warning"
        except Exception:
            msgs.append("Source quantity '" + qraw + "' is not numeric - review.")
            status = "Error"

    # ---- opening balance requires full mapping + valuation
    if r.record_type == "Opening Balance":
        if not r.item_code:
            msgs.append("Opening balance needs a mapped Item.")
            status = "Error"
        if not r.warehouse:
            msgs.append("Opening balance needs a mapped Warehouse.")
            status = "Error"
        if not r.uom:
            msgs.append("Opening balance needs a mapped UOM.")
            status = "Error"
        if not r.qty:
            msgs.append("Opening balance needs a mapped Quantity.")
            status = "Error"
        if not r.valuation_rate:
            msgs.append("Opening balance missing valuation data - review (do not guess).")
            if status == "Valid":
                status = "Warning"

    # ---- classification guards
    if r.record_type in ["Property / Fixed Asset", "Form / Voucher", "Biological Asset"]:
        msgs.append("Non-consumable classification - confirm handling with Finance/Property.")
        if status == "Valid":
            status = "Warning"
    if r.record_type in ["", "Unknown"]:
        msgs.append("Record type not classified - map before import.")
        if status == "Valid":
            status = "Warning"

    # ---- store mapping
    if (r.raw_store or "").strip() and not r.warehouse:
        msgs.append("Source store '" + (r.raw_store or "") + "' is not mapped to a Warehouse.")
        if status == "Valid":
            status = "Warning"

    # ---- duplicate candidate (flag only)
    isdup = 0
    nm = (r.raw_item_name or "").strip().lower()
    cd = (r.item_code or "").strip()
    if cd and code_freq.get(cd, 0) > 1:
        isdup = 1
    elif nm and name_freq.get(nm, 0) > 1:
        isdup = 1
    r.is_duplicate_candidate = isdup
    if isdup:
        msgs.append("Possible duplicate within the batch - review, do not auto-merge.")
        if status == "Valid":
            status = "Warning"

    r.validation_status = status
    r.validation_messages = "\\n".join(msgs)
    if status == "Valid":
        valid += 1
    elif status == "Warning":
        warn += 1
    else:
        err += 1
    if isdup:
        dup += 1

doc.valid_rows = valid
doc.warning_rows = warn
doc.error_rows = err
doc.duplicate_rows = dup
if len(rows) and not err and doc.status in ["Draft", "Staged"]:
    doc.status = "Validated"
"""

set_script("AIG - Migration Batch Validation", "AIG Stock Migration Batch",
           "Before Save", VALIDATION)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP46_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
