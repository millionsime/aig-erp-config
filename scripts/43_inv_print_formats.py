# AIG config - step 43: INVENTORY print formats (config layer, no core edits).
# Creates filing-ready Jinja Print Formats that preserve the source form names:
#   * AIG Quality Form          (Quality Inspection)  - receiving inspection record
#   * AIG Model 19 Stock Request(Material Request)    - request document
#   * AIG Model 22 Issue Note   (Stock Entry)         - printable issue document
#   * AIG Receipt Confirmation  (Material Request)    - end-user receipt evidence
# FLAG: the original Model 19 / Model 22 / Quality Form artwork and numbering rules
# were NOT supplied, so these are clean configurable templates that state the
# document type and reference; AIG can replace the HTML with exact form artwork.
# Idempotent: re-running refreshes the HTML. Module "Stock" (valid ERPNext module).
import frappe
import traceback

MODULE = "Stock"
LOG = []


def log(what, detail):
    LOG.append(f"{what}: {detail}")
    print(f"### {what}: {detail}")


def set_print_format(name, doc_type, html):
    if frappe.db.exists("Print Format", name):
        pf = frappe.get_doc("Print Format", name)
        if pf.html != html or pf.doc_type != doc_type or pf.disabled:
            pf.html = html
            pf.doc_type = doc_type
            pf.print_format_type = "Jinja"
            pf.module = MODULE
            pf.standard = "No"
            pf.disabled = 0
            pf.flags.ignore_permissions = True
            pf.save(ignore_permissions=True)
            log("UPDATE", f"Print Format {name}")
        else:
            log("EXISTS", f"Print Format {name}")
        return name
    doc = frappe.get_doc({
        "doctype": "Print Format", "name": name, "doc_type": doc_type,
        "module": MODULE, "print_format_type": "Jinja", "standard": "No",
        "html": html, "disabled": 0, "raw_printing": 0,
    })
    doc.flags.ignore_permissions = True
    try:
        doc.insert(ignore_permissions=True)
        log("CREATE", f"Print Format {name}")
    except Exception:
        print(f"!! FAILED {name}")
        print(traceback.format_exc())
    return name


STYLE = """
<style>
  .aig-pf { font-family: Arial, Helvetica, sans-serif; color:#111; font-size:12px; }
  .aig-pf h2 { margin:0 0 2px 0; font-size:18px; letter-spacing:.5px; }
  .aig-pf .sub { color:#555; font-size:11px; margin-bottom:8px; }
  .aig-pf table.meta { width:100%; border-collapse:collapse; margin-bottom:10px; }
  .aig-pf table.meta td { padding:3px 6px; border:1px solid #ccc; }
  .aig-pf table.meta td.k { background:#f2f2f2; width:22%; font-weight:bold; }
  .aig-pf table.grid { width:100%; border-collapse:collapse; margin-bottom:10px; }
  .aig-pf table.grid th, .aig-pf table.grid td { border:1px solid #999; padding:4px 6px; text-align:left; }
  .aig-pf table.grid th { background:#e8e8e8; }
  .aig-pf .right { text-align:right; }
  .aig-pf .sig { width:100%; border-collapse:collapse; margin-top:26px; }
  .aig-pf .sig td { width:33%; padding-top:34px; border-top:1px solid #333; text-align:center; font-size:11px; }
  .aig-pf .note { color:#666; font-size:10px; margin-top:14px; border-top:1px dashed #bbb; padding-top:6px; }
</style>
"""

FOOTER = ("<div class='note'>AIG configurable print template. Original form artwork / "
          "pre-printed numbering not supplied - replace this layout with the official "
          "form if required. Generated {{ frappe.utils.now() }}.</div>")

# ------------------------------------------------------------------ Quality Form
QUALITY_FORM = STYLE + """
<div class="aig-pf">
  <h2>QUALITY FORM &mdash; RECEIVING INSPECTION</h2>
  <div class="sub">Adama Investment Group &middot; Quality Inspection {{ doc.name or '' }}</div>
  <table class="meta">
    <tr>
      <td class="k">Inspection Type</td><td>{{ doc.inspection_type or '' }}</td>
      <td class="k">Status</td><td>{{ doc.status or '' }}</td>
    </tr>
    <tr>
      <td class="k">Reference</td><td>{{ doc.reference_type or '' }} {{ doc.reference_name or '' }}</td>
      <td class="k">Inspected By</td><td>{{ doc.inspected_by or '' }}</td>
    </tr>
    <tr>
      <td class="k">Item Code</td><td>{{ doc.item_code or '' }}</td>
      <td class="k">Item Name</td><td>{{ doc.item_name or '' }}</td>
    </tr>
    <tr>
      <td class="k">Sample Size</td><td>{{ doc.sample_size or '' }}</td>
      <td class="k">Date</td><td>{{ (doc.inspection_date or doc.creation or '') }}</td>
    </tr>
  </table>

  <table class="grid">
    <tr><th>Quantity Result</th><th class="right">Qty</th><th>Notes</th></tr>
    <tr><td>Accepted</td><td class="right">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>Rejected</td><td class="right">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>Damaged</td><td class="right">&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>Short</td><td class="right">&nbsp;</td><td>&nbsp;</td></tr>
  </table>

  <table class="meta">
    <tr><td class="k">Inspection Remarks</td><td>{{ doc.remarks or '' }}</td></tr>
  </table>

  <table class="sig">
    <tr>
      <td>Store Keeper (Inspector)</td>
      <td>General Store Keeper (Approver)</td>
      <td>Property Admin (Bin/Tag)</td>
    </tr>
  </table>
  """ + FOOTER + """
</div>
"""
set_print_format("AIG Quality Form", "Quality Inspection", QUALITY_FORM)

# ------------------------------------------------------------------ Model 19
MODEL19 = STYLE + """
<div class="aig-pf">
  <h2>MODEL 19 &mdash; STOCK REQUEST</h2>
  <div class="sub">Adama Investment Group &middot; Material Request {{ doc.name or '' }}</div>
  <table class="meta">
    <tr>
      <td class="k">Request No.</td><td>{{ doc.name or '' }}</td>
      <td class="k">Date</td><td>{{ doc.transaction_date or doc.creation or '' }}</td>
    </tr>
    <tr>
      <td class="k">Requested By</td><td>{{ doc.aig_requested_by or doc.owner or '' }}</td>
      <td class="k">Enterprise (Cost Center)</td><td>{{ doc.aig_cost_center or '' }}</td>
    </tr>
    <tr>
      <td class="k">Request Type</td><td>{{ doc.material_request_type or '' }}</td>
      <td class="k">Needed By</td><td>{{ doc.schedule_date or '' }}</td>
    </tr>
    <tr>
      <td class="k">Destination Store</td><td>{{ doc.aig_destination_warehouse or '' }}</td>
      <td class="k">Status</td><td>{{ doc.workflow_state or '' }}</td>
    </tr>
    <tr><td class="k">Purpose</td><td colspan="3">{{ doc.aig_purpose_note or '' }}</td></tr>
  </table>

  <table class="grid">
    <tr><th>#</th><th>Item Code</th><th>Description</th><th class="right">Qty</th><th>UOM</th><th>Store</th></tr>
    {% for row in (doc.items or []) %}
    <tr>
      <td>{{ row.idx }}</td>
      <td>{{ row.item_code or '' }}</td>
      <td>{{ row.item_name or row.description or '' }}</td>
      <td class="right">{{ row.qty }}</td>
      <td>{{ row.uom or '' }}</td>
      <td>{{ row.warehouse or '' }}</td>
    </tr>
    {% endfor %}
  </table>

  <table class="meta">
    <tr>
      <td class="k">Budget Checked</td><td>{{ 'Yes' if doc.aig_budget_checked else 'No' }}</td>
      <td class="k">Budget Note</td><td>{{ doc.aig_budget_note or '' }}</td>
    </tr>
  </table>

  <table class="sig">
    <tr>
      <td>Requester</td>
      <td>Main Store Administrator</td>
      <td>Enterprise Manager / Director</td>
    </tr>
  </table>
  """ + FOOTER + """
</div>
"""
set_print_format("AIG Model 19 Stock Request", "Material Request", MODEL19)

# ------------------------------------------------------------------ Model 22
MODEL22 = STYLE + """
<div class="aig-pf">
  <h2>MODEL 22 &mdash; STORE ISSUE NOTE</h2>
  <div class="sub">Adama Investment Group &middot; Stock Entry {{ doc.name or '' }}</div>
  <table class="meta">
    <tr>
      <td class="k">Issue No.</td><td>{{ doc.name or '' }}</td>
      <td class="k">Posting Date</td><td>{{ doc.posting_date or '' }}</td>
    </tr>
    <tr>
      <td class="k">Against Request (Model 19)</td><td>{{ doc.aig_material_request or '' }}</td>
      <td class="k">Purpose</td><td>{{ doc.purpose or '' }}</td>
    </tr>
    <tr>
      <td class="k">Issued From (Store)</td><td>{{ doc.from_warehouse or '' }}</td>
      <td class="k">Enterprise (Cost Center)</td><td>{{ doc.aig_cost_center or '' }}</td>
    </tr>
    <tr>
      <td class="k">Issued To (Recipient)</td><td>{{ doc.aig_issued_to or '' }}</td>
      <td class="k">Source / Reference</td><td>{{ doc.aig_source_ref or '' }}</td>
    </tr>
  </table>

  <table class="grid">
    <tr><th>#</th><th>Item Code</th><th>Description</th><th class="right">Qty Issued</th><th>UOM</th><th>Bin</th></tr>
    {% for row in (doc.items or []) %}
    <tr>
      <td>{{ row.idx }}</td>
      <td>{{ row.item_code or '' }}</td>
      <td>{{ row.item_name or row.description or '' }}</td>
      <td class="right">{{ row.qty }}</td>
      <td>{{ row.uom or '' }}</td>
      <td>{{ row.aig_bin_location or '' }}</td>
    </tr>
    {% endfor %}
  </table>

  <table class="sig">
    <tr>
      <td>Issued By (Store Keeper)</td>
      <td>Received By (End User)</td>
      <td>Authorized (Main Store Admin)</td>
    </tr>
  </table>
  """ + FOOTER + """
</div>
"""
set_print_format("AIG Model 22 Issue Note", "Stock Entry", MODEL22)

# ------------------------------------------------------------------ Receipt Confirmation
RECEIPT_CONFIRM = STYLE + """
<div class="aig-pf">
  <h2>ISSUE / RECEIPT CONFIRMATION</h2>
  <div class="sub">Adama Investment Group &middot; Material Request {{ doc.name or '' }}</div>
  <table class="meta">
    <tr>
      <td class="k">Request No. (Model 19)</td><td>{{ doc.name or '' }}</td>
      <td class="k">Issue Reference (Model 22)</td><td>{{ doc.aig_issue_reference or '' }}</td>
    </tr>
    <tr>
      <td class="k">Enterprise (Cost Center)</td><td>{{ doc.aig_cost_center or '' }}</td>
      <td class="k">Received By</td><td>{{ doc.aig_received_by or doc.aig_requested_by or '' }}</td>
    </tr>
    <tr>
      <td class="k">Received On</td><td>{{ doc.aig_received_on or '' }}</td>
      <td class="k">Receipt Confirmed</td><td>{{ 'Yes' if doc.aig_receipt_confirmed else 'No' }}</td>
    </tr>
    <tr><td class="k">Confirmation Note</td><td colspan="3">{{ doc.aig_receipt_note or '' }}</td></tr>
  </table>

  <table class="grid">
    <tr><th>#</th><th>Item Code</th><th>Description</th><th class="right">Requested</th><th>UOM</th></tr>
    {% for row in (doc.items or []) %}
    <tr>
      <td>{{ row.idx }}</td>
      <td>{{ row.item_code or '' }}</td>
      <td>{{ row.item_name or row.description or '' }}</td>
      <td class="right">{{ row.qty }}</td>
      <td>{{ row.uom or '' }}</td>
    </tr>
    {% endfor %}
  </table>

  <table class="sig">
    <tr>
      <td>End User (Receipt Confirmed)</td>
      <td>Store Keeper</td>
      <td>Date</td>
    </tr>
  </table>
  """ + FOOTER + """
</div>
"""
set_print_format("AIG Receipt Confirmation", "Material Request", RECEIPT_CONFIRM)

frappe.db.commit()
frappe.clear_cache()
print(f"\nSTEP43_COMPLETE {len(LOG)} actions")


def run():
    frappe.db.commit()
    return len(LOG)
