# Spreadsheet vs pandas - same cleaning step, two tools

**Step:** take the Sacnilk day-wise table, keep only the `Day N` rows (drop `Week N Collection` and `Total`), turn
`₹ 53.60 Cr [En: 29.60; Hi: 16.00; Ta: 4.00; Te: 4.00]` into numbers (total, English, Hindi) and flag the `** Approx` days.

| | Spreadsheet (`spreadsheet/endgame_daywise_cleaning.xlsx`) | pandas (`spreadsheet/compare_with_pandas.py`, same logic as `src/s02_clean_box_office.py`) |
|---|---|---|
| Filter day rows | `=IF(LEFT(A2,4)="Day ","yes","no")` then filter column C | `t[t["label"].str.startswith("Day ")]` |
| Text → number | `=VALUE(TRIM(MID(B2,FIND("₹",B2)+1,FIND("Cr",B2)-FIND("₹",B2)-1)))` | `.str.extract(r"₹\s*([\d.]+)\s*Cr").astype(float)` |
| Language split | nested `FIND("En:")` / `FIND(";")` inside `MID` | `.str.extract(r"En:\s*([\d.]+)")` |
| Approx flag | `=IF(ISNUMBER(SEARCH("~*~*",B2)),"approx","reported")` (the `~` escapes `*`) | `.str.contains(r"\*\*")` |
| Result | 21 day rows, total ₹361.05 Cr | 21 day rows, total ₹361.05 Cr - **all 21 rows match** (script prints the check) |

**What we noticed**
- The spreadsheet was quicker to *see* - you spot the Week rows and the `**` immediately, and anyone in the team can check a cell.
- The formulas are fragile: the `Hi:` formula would return `#VALUE!` on the Week 5 row (`[En: 2.40; Hi: 0.60]` has no `;` after the Hindi value) - one more reason to filter to day rows first. And `*` is a wildcard in `SEARCH`, so it needs `~*`. We had to look that up.
- pandas is one line per rule, reusable for Bollywood Hungama's `₹53.6 cr.` format and the `Lac` values with the same `parse_inr_to_crore()` function, and it reruns on new data with no copy-pasting.
- Decision: spreadsheet for eyeballing and quick checks, pandas for the pipeline.
