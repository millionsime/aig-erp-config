# AIG foundation - BUILD E: Ethiopian (Ge'ez) date DISPLAY fields.
# Scope (brief 5.3, accepted as display-only): a read-only HTML field on key
# doctypes showing the Ethiopic equivalent of the operative Gregorian date.
# The HTML fieldtype stores NOTHING - pure cosmetic render via Client Script.
# The conversion algorithm was anchor-verified + 1826-day sweep tested
# (scripts/ethiopic_test.js) BEFORE deployment. No core JS is touched.

JS_TEMPLATE = """// AIG - Ethiopian (Ge'ez) date display - READ-ONLY reference only.
// The operative/posting date stays Gregorian. This display field stores
// nothing (HTML fieldtype) and does not affect validation, fiscal periods,
// or workflows. Algorithm verified against calendar anchors before deploy.
(function () {
\tconst MONTHS = ["Meskerem","Tikimt","Hidar","Tahsas","Tir","Yekatit","Megabit",
\t\t"Miyazya","Ginbot","Sene","Hamle","Nehase","Pagume"];
\tconst EPOCH = 1724223; // JDN of 1 Meskerem 1 EC (Amete Mihret; leap years = 3 mod 4)

\tfunction g2j(y, m, d) {
\t\treturn Math.floor((1461 * (y + 4800 + Math.floor((m - 14) / 12))) / 4)
\t\t\t+ Math.floor((367 * (m - 2 - 12 * Math.floor((m - 14) / 12))) / 12)
\t\t\t- Math.floor((3 * Math.floor((y + 4900 + Math.floor((m - 14) / 12)) / 100)) / 4)
\t\t\t+ d - 32075;
\t}
\tfunction j2e(jdn) {
\t\tconst days = jdn - EPOCH;
\t\tif (days < 0) return null;
\t\tconst cycle = Math.floor(days / 1461);
\t\tconst idx = days % 1461;
\t\tlet year, doy;
\t\tif (idx < 365) { year = 1; doy = idx; }
\t\telse if (idx < 730) { year = 2; doy = idx - 365; }
\t\telse if (idx < 1096) { year = 3; doy = idx - 730; }
\t\telse { year = 4; doy = idx - 1096; }
\t\tyear = cycle * 4 + year;
\t\tlet month, day;
\t\tif (doy < 360) { month = Math.floor(doy / 30) + 1; day = (doy % 30) + 1; }
\t\telse { month = 13; day = doy - 359; }
\t\treturn { year: year, month: month, day: day, monthName: MONTHS[month - 1] };
\t}
\tfunction toEth(greg) {
\t\tif (!greg) return null;
\t\tconst parts = greg.split("-");
\t\tif (parts.length !== 3) return null;
\t\tconst y = +parts[0], m = +parts[1], d = +parts[2];
\t\tif (!y || !m || !d) return null;
\t\treturn j2e(g2j(y, m, d));
\t}
\tfunction update(frm) {
\t\tconst f = frm.fields_dict.aig_eth_date_display;
\t\tif (!f || !f.$wrapper) return;
\t\tconst e = toEth(frm.doc.__DATE_FIELD__);
\t\tconst txt = e ? (e.day + " " + e.monthName + " " + e.year + " EC") : "\\u2014";
\t\tf.$wrapper.html(
\t\t\t'<div style="padding:2px 0;font-weight:500;color:#3d4657;">'
\t\t\t+ '<span title="Ethiopian (Ge\\u2019ez) calendar equivalent - display only">'
\t\t\t+ txt + '</span></div>'
\t\t);
\t}
\tfrappe.ui.form.on("__DOCTYPE__", {
\t\trefresh: update,
\t\t__DATE_FIELD__: update
\t});
})();
"""

TARGETS = [
    ("Purchase Order", "transaction_date"),
    ("Journal Entry", "posting_date"),
    ("Payment Entry", "posting_date"),
    ("Attendance", "attendance_date"),
]

from frappe.custom.doctype.custom_field.custom_field import create_custom_field

for dt, date_field in TARGETS:
    if not frappe.db.exists("Custom Field", f"{dt}-aig_eth_date_display"):
        create_custom_field(dt, {
            "fieldname": "aig_eth_date_display",
            "label": "Ethiopian Date (EC)",
            "fieldtype": "HTML",
            "insert_after": date_field,
            "print_hide": 1,
            "no_copy": 1,
            "owner": "Administrator",
        }, ignore_validate=True)
        print("CREATED Custom Field:", dt, ".aig_eth_date_display")
    else:
        print("Custom Field exists:", dt)

    js = JS_TEMPLATE.replace("__DOCTYPE__", dt).replace("__DATE_FIELD__", date_field)
    existing = frappe.get_all("Client Script", filters={"dt": dt, "view": "Form"}, pluck="name")
    marker_hit = None
    for n in existing:
        if "aig_eth_date_display" in (frappe.db.get_value("Client Script", n, "script") or ""):
            marker_hit = n
            break
    if marker_hit:
        s = frappe.get_doc("Client Script", marker_hit)
        s.script = js
        s.enabled = 1
        s.save()
        print("UPDATED Client Script:", marker_hit)
    else:
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "name": f"AIG - Ethiopic Date ({dt})",  # autoname = Prompt
            "dt": dt,
            "view": "Form",
            "enabled": 1,
            "script": js,
        }).insert()
        print("CREATED Client Script:", doc.name, f"({dt} / {date_field})")

print("\nVERIFY:")
for dt, _ in TARGETS:
    cf = frappe.db.get_value("Custom Field", f"{dt}-aig_eth_date_display",
                             ["fieldtype", "insert_after"], as_dict=True)
    print(" ", dt, "->", cf)
print("Client Scripts:", frappe.get_all("Client Script",
      filters={"script": ["like", "%aig_eth_date_display%"]}, pluck="name"))
print("\nDONE-E")
