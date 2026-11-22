"""
Spreadsheet vs pandas - the SAME cleaning step done twice.

Step: Sacnilk day-wise table -> keep only 'Day N' rows, turn '₹ 53.60 Cr [En: 29.60; Hi: 16.00; ...]'
into numbers (total, English, Hindi) and flag the '** Approx' days.

Spreadsheet version: spreadsheet/endgame_daywise_cleaning.xlsx (formulas in columns C-G)
pandas version     : below (same logic as src/s02_clean_box_office.py)

    python spreadsheet/compare_with_pandas.py
Note: the xlsx must have been opened & saved in Excel/LibreOffice once so the formula
results are stored in the file (openpyxl reads cached values only).
"""
from io import StringIO
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# ---------------- pandas
html = (ROOT / "data" / "raw" / "box_office" / "sacnilk_endgame_daywise_table.html").read_text(encoding="utf-8")
t = pd.read_html(StringIO(html))[0]
t.columns = ["label", "net_text", "change"]
t = t[t["label"].str.startswith("Day ")].copy()
t["net_cr"] = t["net_text"].str.extract(r"₹\s*([\d.]+)\s*Cr").astype(float)
t["english_cr"] = t["net_text"].str.extract(r"En:\s*([\d.]+)").astype(float)
t["hindi_cr"] = t["net_text"].str.extract(r"Hi:\s*([\d.]+)").astype(float)
t["approx"] = t["net_text"].str.contains(r"\*\*").map({True: "approx", False: "reported"})

# ---------------- spreadsheet (cached formula results)
x = pd.read_excel(HERE / "endgame_daywise_cleaning.xlsx", nrows=27)
x = x[x["Is it a day row?"] == "yes"].reset_index(drop=True)

cmp = pd.DataFrame({
    "label": t["label"].values,
    "pandas_net": t["net_cr"].values, "excel_net": x["Net ₹ Cr (formula)"].astype(float).values,
    "pandas_en": t["english_cr"].values, "excel_en": x["English ₹ Cr (formula)"].astype(float).values,
    "pandas_flag": t["approx"].values, "excel_flag": x["Approx? (formula)"].values,
})
cmp["all_match"] = ((cmp.pandas_net - cmp.excel_net).abs() < 1e-9) & ((cmp.pandas_en - cmp.excel_en).abs() < 1e-9) \
                   & (cmp.pandas_flag == cmp.excel_flag)
print(cmp.to_string(index=False))
print(f"\nrows: pandas {len(t)}, spreadsheet {len(x)}; all match: {cmp['all_match'].all()}")
print(f"total net: pandas {t['net_cr'].sum():.2f} vs spreadsheet {x['Net ₹ Cr (formula)'].astype(float).sum():.2f}")
