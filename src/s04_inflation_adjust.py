"""
Step 4 - inflation: turn 2019 rupees into Oct-2026 rupees using official CPI.

Problem: CPI changed base in Feb 2026 (2012=100 -> 2024=100). The two series are NOT
directly comparable (141.2 in Apr-2019 vs 110.05 in Oct-2026 does not mean prices fell!).
MoSPI published a linking factor for exactly this:  CPI_linked = CPI_old x 0.5267 (Combined).

Inputs  : data/raw/cpi/*.csv, data/interim/daily_collections.csv, weekly_collections.csv
Outputs : data/interim/cpi_monthly.csv, data/interim/daily_collections_real.csv,
          outputs/tables/inflation_summary.csv
"""
import pandas as pd

from config import RAW, INTERIM, TABLES, CPI_TARGET_MONTH
from utils import CleaningLog

log = CleaningLog("s04_inflation")

cpi = pd.read_csv(RAW / "cpi" / "cpi_all_india_general_index.csv")
lf = pd.read_csv(RAW / "cpi" / "cpi_linking_factors_2012_to_2024.csv")
LF = float(lf.loc[lf["sector"] == "Combined", "linking_factor"].iloc[0])

cpi["month_dt"] = pd.to_datetime(cpi["month"], format="%b-%Y")
old = cpi[cpi["series_base"] == "2012=100"].set_index("month_dt")["index_value"]
new = cpi[cpi["series_base"] == "2024=100"].set_index("month_dt")["index_value"]

months = sorted(set(old.index) | set(new.index))
cpi_m = pd.DataFrame({"month": months})
cpi_m["cpi_base2012"] = cpi_m["month"].map(old)
cpi_m["cpi_base2024"] = cpi_m["month"].map(new)
# use the new series where it exists, otherwise link the old one
cpi_m["cpi_linked_2024"] = cpi_m["cpi_base2024"].fillna((cpi_m["cpi_base2012"] * LF).round(2))
cpi_m["series_used"] = cpi_m["cpi_base2024"].notna().map({True: "2024=100 (published)", False: f"2012=100 x {LF} (linked)"})
log.add("cpi", "CPI base changed from 2012=100 to 2024=100 in Feb 2026", int(cpi_m["cpi_base2024"].isna().sum()),
        f"old-base months multiplied by MoSPI linking factor {LF} (Combined)",
        "official linking method; never mix raw 2012-base and 2024-base numbers")

# sanity check: Dec-2025 exists in both series -> linked old should be close to the published new value
both = cpi_m.dropna(subset=["cpi_base2012", "cpi_base2024"])
for _, r in both.iterrows():
    gap = r.cpi_base2012 * LF - r.cpi_base2024
    log.add("cpi", f"overlap check {r.month:%b-%Y}: linked old = {r.cpi_base2012 * LF:.2f} vs published new = {r.cpi_base2024}",
            1, "no change, reported", f"gap {gap:+.2f} points shows the link is approximate (factor is an annual average)")

cpi_m.to_csv(INTERIM / "cpi_monthly.csv", index=False)

target = pd.Timestamp(pd.to_datetime(CPI_TARGET_MONTH, format="%b-%Y"))
cpi_target = float(cpi_m.loc[cpi_m["month"] == target, "cpi_linked_2024"].iloc[0])
lookup = cpi_m.set_index("month")["cpi_linked_2024"]

# ------------------------------------------------------------------ daily collections in real terms
daily = pd.read_csv(INTERIM / "daily_collections.csv", parse_dates=["date"])
daily["month"] = daily["date"].dt.to_period("M").dt.to_timestamp()
daily["cpi_month"] = daily["month"].map(lookup)

missing_cpi = daily["cpi_month"].isna()
if missing_cpi.any():
    # Nov-2026 CPI is released on 14 Dec 2026 - not out yet. Use latest available month.
    daily.loc[missing_cpi, "cpi_month"] = cpi_target
    log.add("daily_collections", "CPI for Nov-2026 not published yet (release 14-Dec-2026)", int(missing_cpi.sum()),
            f"used {CPI_TARGET_MONTH} CPI (latest available)", "one-month gap, effect < 1%")

daily["cpi_factor_to_target"] = (cpi_target / daily["cpi_month"]).round(4)
daily["net_cr_real"] = (daily["net_cr"] * daily["cpi_factor_to_target"]).round(3)
daily["gross_cr_est_real"] = (daily["gross_cr_est"] * daily["cpi_factor_to_target"]).round(3)
daily.to_csv(INTERIM / "daily_collections_real.csv", index=False)

# ------------------------------------------------------------------ summary table for the report
f_apr19 = cpi_target / lookup[pd.Timestamp("2019-04-01")]
rows = []


def add(metric, nominal, factor, note):
    rows.append({"metric": metric, "nominal_cr": nominal, "cpi_factor": round(factor, 4),
                 f"real_cr_{CPI_TARGET_MONTH}": round(nominal * factor, 2), "note": note})


eg = daily[daily["film_key"] == "AVG_ENDGAME_2019"]
add("Endgame opening day (Fri 26-Apr-2019) net", eg.loc[eg.day_no == 1, "net_cr"].iloc[0], f_apr19, "Sacnilk/BH day table")
add("Endgame opening weekend (3 days) net", eg.loc[eg.day_no <= 3, "net_cr"].sum(), f_apr19, "")
add("Endgame week 1 net", eg.loc[eg.day_no <= 7, "net_cr"].sum(), f_apr19, "")
add("Endgame lifetime net - low (Sacnilk summary)", 370.05, f_apr19, "sources disagree, so we show a range")
add("Endgame lifetime net - high (BH total)", 373.22, f_apr19, "")
add("Endgame India gross (Sacnilk)", 445.00, f_apr19, "")
enc = daily[daily["film_key"] == "AVG_ENCORE_2026"]
add("Encore re-release lifetime net (Sep-Nov 2026)", round(enc["net_cr"].sum(), 3), 1.0, "already ~2026 prices (factor ~1.00-1.01)")
summary = pd.DataFrame(rows)
summary.to_csv(TABLES / "inflation_summary.csv", index=False)

# ticket price vs CPI: is cinema-ticket inflation the same as general inflation? (no - see chart)
atp_2019, atp_2026 = 215, 699
tp = pd.DataFrame([{
    "atp_2019_pvr_normal_rs": atp_2019,
    "atp_2019_in_oct2026_rs_cpi": round(atp_2019 * f_apr19),
    "atp_doomsday_day1_advance_rs": atp_2026,
    "cpi_growth_pct": round((f_apr19 - 1) * 100, 1),
    "ticket_growth_pct": round((atp_2026 / atp_2019 - 1) * 100, 1),
    "caveat": "2019 = PVR chain's normal ATP; 2026 = all-India Day-1 advance ATP incl. premium formats. Different scope -> indicative only.",
}])
tp.to_csv(TABLES / "ticket_price_vs_cpi.csv", index=False)
log.add("ticket_prices", "no like-for-like ATP for Endgame 2019 in public sources", 1,
        "compare PVR normal ATP 2019 (₹215) with Doomsday advance ATP (₹699), flagged as indicative",
        "CPI is not a cinema price index; we keep the two comparisons separate")

print(cpi_m.to_string())
print(summary.to_string())
print(tp.T)
log.save()
