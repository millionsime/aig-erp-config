# Decisions: stock, assets and HR setup (2026-11-21)

Taken by the tech team lead. Items marked **OPEN** go to the named team.

## Stock (to build in `aig_stock`)

| # | Decision |
| --- | --- |
| S-1 | Valuation method: **Moving Average** for all items (P-10). |
| S-2 | Warehouses per enterprise and per site. |
| S-3 | Stores: Head Office – Main Store. Construction – Materials Store, Machinery & Spares Store. Agro – Dairy Farm, Dairy Processing, Poultry Farm, Feed Plant, Abattoir, Flour & Bread Factory, Crop & Horticulture stores. Integrated Services – Fuel Depot, Garage Spares, Cafeteria, City Mall stores. Tech – IT Store. Engineering – Engineering Store. Shared: Goods In Transit, Rejected / Quarantine. |
| S-4 | Item groups by nature: Raw Materials, Finished Goods, Spare Parts & Consumables, Fuel & Lubricants, Livestock, Office Supplies, Fixed Assets, Services; each with default stock, expense and income accounts. |
| S-5 | Supplier goods are received with **Purchase Receipt** (not Stock Entry). Resolves open question 5 of the PO workflow concept note. |
| S-6 | Over-receipt / over-delivery allowance: **0%**. |
| S-7 | Batch + expiry for food, dairy, feed and veterinary drugs; serial numbers for IT, tools and high-value spares. |
| S-8 | Automatic re-order: draft Material Requests when stock reaches the re-order level, **no email**. |
| S-9 | Item codes: naming series **AIG-ITEM-YYYY-#####**. The theme's "AIG - Item Auto Code" script must be reconciled with it. |

## Assets

| # | Decision |
| --- | --- |
| A-1 | Straight line. Buildings 20 yrs, vehicles 5, plant & machinery 10, office equipment 5, furniture 10, computers & IT 4, intangibles over the licence term, land not depreciated. One finance book. |
| A-2 | Capitalisation threshold: **OPEN – Finance.** |
| A-3 | Asset location tree: **OPEN – Property Administration.** |
| A-4 | Assets auto-created on Purchase Receipt; naming **AIG-AST-YYYY-#####**. |

## HR (to build in `aig_hr`)

| # | Decision |
| --- | --- |
| H-1 | Working week Monday–Friday, Saturday half day. |
| H-2 | Office hours 08:30–12:30 and 13:30–17:30; Saturday 08:30–12:30. |
| H-3 | Shift types for farms, fuel station, cafeteria, security: **OPEN – HR.** |
| H-4 | Leave = legal minimums of Labour Proclamation 1156/2019: annual 16 working days in year one, +1 day per two further years of service; sick leave up to 6 months (1 month full pay, 2 months half pay, 3 months unpaid); maternity 120 days (30 before, 90 after birth); paternity 3 days; marriage 3 days; bereavement 3 days. |
| H-5 | Holiday list EFY 2019: all national holidays (Enkutatash, Meskel, Genna, Timket, Adwa, Labour Day, Patriots' Day, Downfall of the Derg, Siklet, Fasika, Eid al-Fitr, Eid al-Adha, Mawlid). Muslim holiday dates confirmed by HR each year. |
| H-6 | Phase 1 is employees, attendance and leave; **payroll is phase 2**. |
| H-7 | Employment types Permanent, Contract, Probation, Temporary/Daily, Intern. Grade / job-level scale: **OPEN – HR.** |
| H-8 | `aig_hr` is transferred to `millionsime` and built like `aig-finance` (private, read token). |
