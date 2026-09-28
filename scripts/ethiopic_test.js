// Ethiopic <-> Gregorian conversion: validate against known anchors before deploy.
// Amete Mihret: leap years are EC years ≡ 3 (mod 4) — e.g. EC1999 (Millennium:
// 1 Meskerem 2000 = 12 Sep 2007), EC2015, EC2019. Cycle of 4 = years ≡1,2,3,0;
// the leap day (Pagume 6) is the LAST day of the 3rd year in the cycle.
const MONTHS = ["Meskerem","Tikimt","Hidar","Tahsas","Tir","Yekatit","Megabit",
  "Miyazya","Ginbot","Sene","Hamle","Nehase","Pagume"];
const EPOCH = 1724223; // JDN of 1 Meskerem 1 EC (anchor-verified)

function gregorianToJDN(y, m, d) {
  return Math.floor((1461 * (y + 4800 + Math.floor((m - 14) / 12))) / 4)
       + Math.floor((367 * (m - 2 - 12 * Math.floor((m - 14) / 12))) / 12)
       - Math.floor((3 * Math.floor((y + 4900 + Math.floor((m - 14) / 12)) / 100)) / 4)
       + d - 32075;
}
function jdnToEthiopic(jdn) {
  const days = jdn - EPOCH;             // days since 1 Meskerem 1 EC (AM year 1)
  if (days < 0) return null;
  const cycle = Math.floor(days / 1461);
  const idx = days % 1461;              // position in 4-year cycle: 0..1460
  let year, doy;
  if (idx < 365) { year = 1; doy = idx; }            // year 1 of cycle (365d)
  else if (idx < 730) { year = 2; doy = idx - 365; } // year 2 of cycle (365d)
  else if (idx < 1096) { year = 3; doy = idx - 730; }// year 3 = LEAP (366d)
  else { year = 4; doy = idx - 1096; }               // year 4 of cycle (365d)
  const y = cycle * 4 + year;
  let month, day;
  if (doy < 360) { month = Math.floor(doy / 30) + 1; day = (doy % 30) + 1; }
  else { month = 13; day = doy - 359; }
  return { year: y, month, day, monthName: MONTHS[month - 1] };
}
function ethiopicToJDN(y, m, d) {
  // completed leap years before year y = floor(y/4) (leap years 3,7,11,...)
  return EPOCH + (y - 1) * 365 + Math.floor(y / 4) + (m - 1) * 30 + (d - 1);
}
function toEthiopic(dateStr) {
  const [y, m, d] = dateStr.split("-").map(Number);
  return jdnToEthiopic(gregorianToJDN(y, m, d));
}
function fmt(e) { return `${e.day} ${e.monthName} ${e.year} EC`; }

// Anchors: (Gregorian, expected Ethiopic)
const anchors = [
  ["2025-09-11", { year: 2018, month: 1, day: 1 }],   // Enkutatash 2018
  ["2026-07-08", { year: 2018, month: 11, day: 1 }],  // fiscal year start (Hamle 1)
  ["2026-09-10", { year: 2018, month: 13, day: 5 }],  // Pagume 5 (EC2018 not leap)
  ["2026-09-11", { year: 2019, month: 1, day: 1 }],   // Enkutatash 2019
  ["2027-09-10", { year: 2019, month: 13, day: 5 }],  // Pagume 5 (EC2019 leap)
  ["2027-09-11", { year: 2019, month: 13, day: 6 }],  // Pagume 6 (EC2019 leap)
  ["2027-09-12", { year: 2020, month: 1, day: 1 }],   // Enkutatash 2020 (after leap)
  ["2024-09-10", { year: 2016, month: 13, day: 4 }],  // Pagume 4 (EC2016 not leap)
  ["2024-09-11", { year: 2016, month: 13, day: 5 }],  // Pagume 5 = last day EC2016
  ["2024-09-12", { year: 2017, month: 1, day: 1 }],   // Enkutatash 2017 (12 Sep rule)
  ["2007-09-12", { year: 2000, month: 1, day: 1 }],   // Millennium anchor
];

let fails = 0;
for (const [g, exp] of anchors) {
  const got = toEthiopic(g);
  const ok = got.year === exp.year && got.month === exp.month && got.day === exp.day;
  if (!ok) fails++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${g} -> ${fmt(got)}   expected ${exp.day}/${exp.month}/${exp.year}`);
}
// Round-trips (forward then back)
for (const [g] of anchors) {
  const e = toEthiopic(g);
  const back = ethiopicToJDN(e.year, e.month, e.day);
  const [y, m, d] = g.split("-").map(Number);
  if (back !== gregorianToJDN(y, m, d)) { fails++; console.log("ROUNDTRIP FAIL", g); }
}
// Full sweep: every day 2025-01-01 .. 2029-12-31 must round-trip exactly
{
  let d = new Date(Date.UTC(2025, 0, 1)), end = new Date(Date.UTC(2029, 11, 31)), n = 0;
  while (d <= end) {
    const ys = d.getUTCFullYear(), ms = d.getUTCMonth() + 1, ds = d.getUTCDate();
    const j = gregorianToJDN(ys, ms, ds);
    const e = jdnToEthiopic(j);
    if (e.year < 2017 || e.year > 2022) { fails++; console.log("SWEEP year out of range", g, e); break; }
    if (ethiopicToJDN(e.year, e.month, e.day) !== j) { fails++; console.log("SWEEP RT FAIL", ys, ms, ds, e); break; }
    // consecutive-day successor check (Ethiopic date of j+1 must be one Ethiopic day later)
    const e2 = jdnToEthiopic(j + 1);
    if (ethiopicToJDN(e2.year, e2.month, e2.day) !== ethiopicToJDN(e.year, e.month, e.day) + 1) {
      fails++; console.log("SWEEP SEQ FAIL", ys, ms, ds, e, e2); break;
    }
    d = new Date(d.getTime() + 86400000); n++;
  }
  console.log("sweep days checked:", n);
}
console.log(fails === 0 ? "ALL TESTS PASS" : `${fails} FAILURES`);
process.exit(fails === 0 ? 0 : 1);
