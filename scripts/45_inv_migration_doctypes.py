# AIG config - step 45: INVENTORY migration staging DocTypes (config layer).
# Creates two CUSTOM DocTypes (custom=1, stored in DB - no core/app files touched):
#   * AIG Stock Migration Batch - one import run: source workbook/sheet, enterprise,
#     effective date, valuation method, approval + reconciliation counters.
#   * AIG Stock Migration Row   - one source row: full provenance, RAW source values
#     (never overwritten), MAPPED ERP values, classification, and validation results.
# Design honors the brief: preserve provenance, never silently merge/correct, separate
# opening balances from historical movements, require explicit mapping + approval.
import frappe
import traceback

MODULE = "Stock"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def f(fieldname, fieldtype, label=None, **kw):
    d = {"fieldname": fieldname, "fieldtype": fieldtype,
         "label": label or fieldname.replace("_", " ").title()}
    d.update(kw)
    return d


BATCH_FIELDS = [
    f("source_section", "Section Break", "Source"),
    f("source_workbook", "Data", "Source Workbook", reqd=1, in_list_view=1),
    f("source_file", "Attach", "Source File (evidence)"),
    f("sheet_name", "Data", "Sheet Name", reqd=1, in_list_view=1),
    f("column_break_1", "Column Break"),
    f("enterprise", "Link", "Enterprise (Cost Center)", options="Cost Center", in_list_view=1),
    f("effective_date", "Date", "Opening Balance Effective Date"),
    f("valuation_method", "Select", "Valuation Method",
      options="\nMoving Average\nFIFO\nManual (from source)"),
    f("approval_section", "Section Break", "Control"),
    f("status", "Select", "Status",
      options="Draft\nStaged\nValidated\nApproved\nImported\nRejected",
      default="Draft", reqd=1, in_list_view=1),
    f("approved_by", "Link", "Approved By", options="User", read_only_depends_on="eval:doc.status!='Approved'"),
    f("column_break_2", "Column Break"),
    f("approved_on", "Datetime", "Approved On"),
    f("separate_history", "Check", "Keep Historical Movements Separate (do not post as opening)"),
    f("recon_section", "Section Break", "Reconciliation (auto)"),
    f("total_rows", "Int", "Total Rows", read_only=1, in_list_view=1),
    f("valid_rows", "Int", "Valid Rows", read_only=1),
    f("column_break_3", "Column Break"),
    f("warning_rows", "Int", "Warning Rows", read_only=1),
    f("error_rows", "Int", "Error Rows", read_only=1, in_list_view=1),
    f("column_break_4", "Column Break"),
    f("duplicate_rows", "Int", "Duplicate Candidates", read_only=1),
    f("reconciliation_note", "Small Text", "Reconciliation Note"),
    f("rows_section", "Section Break", "Staged Rows"),
    f("rows", "Table", "Staged Rows", options="AIG Stock Migration Row"),
]

ROW_FIELDS = [
    f("prov_section", "Section Break", "Provenance"),
    f("source_workbook", "Data", "Source Workbook"),
    f("sheet_name", "Data", "Sheet Name"),
    f("source_row_no", "Int", "Source Row No."),
    f("source_ref", "Data", "Source Row Reference"),
    f("raw_section", "Section Break", "Raw Source Values (preserved, never overwritten)"),
    f("raw_item_code", "Data", "Raw Item Code"),
    f("raw_item_name", "Data", "Raw Item Name"),
    f("column_break_r1", "Column Break"),
    f("raw_local_name", "Data", "Raw Local/Language Name"),
    f("raw_qty", "Data", "Raw Quantity (as text)"),
    f("column_break_r2", "Column Break"),
    f("raw_uom", "Data", "Raw UOM"),
    f("raw_rate", "Data", "Raw Rate/Price (as text)"),
    f("column_break_r3", "Column Break"),
    f("raw_date", "Data", "Raw Date (as text / Excel serial)"),
    f("raw_store", "Data", "Raw Store"),
    f("column_break_r4", "Column Break"),
    f("raw_department", "Data", "Raw Department"),
    f("raw_enterprise", "Data", "Raw Enterprise"),
    f("raw_notes", "Small Text", "Raw Notes"),
    f("map_section", "Section Break", "Mapped ERP Values (require explicit mapping)"),
    f("record_type", "Select", "Record Type",
      options="\nOpening Balance\nHistorical Movement\nProperty / Fixed Asset\nForm / Voucher\nBiological Asset\nUnknown",
      default="Unknown", in_list_view=1),
    f("item_code", "Link", "Mapped Item", options="Item", in_list_view=1),
    f("column_break_m1", "Column Break"),
    f("item_group", "Link", "Mapped Item Group", options="Item Group"),
    f("warehouse", "Link", "Mapped Warehouse", options="Warehouse", in_list_view=1),
    f("column_break_m2", "Column Break"),
    f("cost_center", "Link", "Mapped Cost Center", options="Cost Center"),
    f("uom", "Link", "Mapped UOM", options="UOM"),
    f("column_break_m3", "Column Break"),
    f("qty", "Float", "Mapped Quantity"),
    f("valuation_rate", "Currency", "Mapped Valuation Rate"),
    f("posting_date", "Date", "Mapped Posting/Effective Date"),
    f("val_section", "Section Break", "Validation (auto)"),
    f("validation_status", "Select", "Validation Status",
      options="Pending\nValid\nWarning\nError", default="Pending", read_only=1, in_list_view=1),
    f("is_duplicate_candidate", "Check", "Duplicate Candidate", read_only=1, in_list_view=1),
    f("column_break_v1", "Column Break"),
    f("date_is_excel_serial", "Check", "Raw Date Was Excel Serial", read_only=1),
    f("date_converted", "Date", "Converted Date", read_only=1),
    f("column_break_v2", "Column Break"),
    f("imported", "Check", "Imported", read_only=1),
    f("target_document", "Data", "Target Document (created on import)", read_only=1),
    f("validation_messages", "Small Text", "Validation Messages", read_only=1),
]


def build_doctype(name, fields, istable, autoname=None, perms=None, title_field=None):
    if frappe.db.exists("DocType", name):
        log("EXISTS", f"DocType {name}")
        return name
    doc = {
        "doctype": "DocType", "name": name, "module": MODULE, "custom": 1,
        "istable": 1 if istable else 0, "track_changes": 1, "editable_grid": 1,
        "fields": fields,
    }
    if autoname:
        doc["autoname"] = autoname
    if title_field:
        doc["title_field"] = title_field
    if perms is not None:
        doc["permissions"] = perms
    d = frappe.get_doc(doc)
    d.flags.ignore_permissions = True
    try:
        d.insert(ignore_permissions=True)
        log("CREATE", f"DocType {name} ({len(fields)} fields)")
    except Exception:
        print(f"!! FAILED DocType {name}")
        print(traceback.format_exc())
    return name


BATCH_PERMS = [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 0, "cancel": 0, "amend": 0},
    {"role": "AIG Inventory Administrator", "read": 1, "write": 1, "create": 1, "delete": 1},
    {"role": "AIG Internal Auditor", "read": 1},
    {"role": "AIG Finance", "read": 1},
]

# child table first (referenced by the batch Table field)
build_doctype("AIG Stock Migration Row", ROW_FIELDS, istable=True)
build_doctype("AIG Stock Migration Batch", BATCH_FIELDS, istable=False,
              autoname="AIG-MIG-.#####", perms=BATCH_PERMS, title_field="source_workbook")

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP45_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
