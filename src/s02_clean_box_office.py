"""
Step 2 - box office tables (structured, HTML / text tables from trade sites).

Inputs  : data/raw/box_office/sacnilk_endgame_daywise_table.html
          data/raw/box_office/bollywoodhungama_endgame_tables.txt
          data/raw/box_office/sacnilk_doomsday_day1_advance_2026-11-21.txt
Outputs : data/interim/daily_collections.csv      (one row per film per day, both sources side by side)
          data/interim/weekly_collections.csv
          data/interim/advance_booking_day1.csv   (Doomsday, by language / state / city)
          outputs/tables/source_disagreements.csv
"""
import re
from io import StringIO

import pandas as pd

from config import RAW, INTERIM, TABLES, FILMS
from utils import CleaningLog, parse_inr_to_crore, parse_indian_count, parse_pct

log = CleaningLog("s02_clean_box_office")
BO = RAW / "box_office"

# =============================================================== Sacnilk (HTML table)
html = (BO / "sacnilk_endgame_daywise_table.html").read_text(encoding="utf-8")
sac = pd.read_html(StringIO(html))[0]
sac.columns = ["label", "net_text", "change_text"]
print("sacnilk rows:", len(sac))

# split day rows from week/total summary rows
is_day = sac["label"].str.match(r"Day \d+")
sac_week = sac[~is_day].copy()
sac = sac[is_day].copy()
log.add("sacnilk_daywise", "table mixes day rows with 'Week N Collection' and 'Total' rows", len(sac_week),
        "moved to a separate weekly table", "summing day + week rows would double count")

sac["day_no"] = sac["label"].str.extract(r"Day (\d+)").astype(int)
sac["net_cr_sacnilk"] = sac["net_text"].map(parse_inr_to_crore)
# language split inside the brackets: [En: 29.60; Hi: 16.00; Ta: 4.00; Te: 4.00]
for code, name in [("En", "english"), ("Hi", "hindi"), ("Ta", "tamil"), ("Te", "telugu")]:
    sac[f"net_cr_{name}"] = sac["net_text"].str.extract(rf"{code}:\s*([\d.]+)").astype(float)
sac["is_approx_sacnilk"] = sac["net_text"].str.contains(r"\*\*")
log.add("sacnilk_daywise", "currency strings like '₹ 53.60 Cr [En: ...]'", len(sac),
        "parsed to float crore + 4 language columns", "type casting text -> numeric")
log.add("sacnilk_daywise", "days 15-21 marked '** Approx' by the source", int(sac["is_approx_sacnilk"].sum()),
        "kept, flagged is_approx=True", "approximate is still the best public figure; flag lets us exclude in robustness checks")

# language split should add up to the day total - check it
lang_sum = sac[[c for c in sac.columns if c.startswith("net_cr_") and c != "net_cr_sacnilk"]].sum(axis=1)
off = (lang_sum - sac["net_cr_sacnilk"]).abs() > 0.011
log.add("sacnilk_daywise", "language split does not add up to the day total", int(off.sum()),
        "kept day total as the official figure", "rounding by the source")

# =============================================================== Bollywood Hungama (text dump of the tables)
raw_txt = (BO / "bollywoodhungama_endgame_tables.txt").read_text(encoding="utf-8")
# drop our '#' header lines first (one of them mentions the separator itself)
raw_txt = "\n".join(l for l in raw_txt.splitlines() if not l.startswith("#"))
blocks = [b.strip() for b in raw_txt.split("<!--next-->")]


def block_to_df(block):
    lines = [l for l in block.splitlines() if l.strip()]
    rows = [[c.strip() for c in l.split("|")] for l in lines]
    width = len(rows[0])
    rows = [r[:width] + [""] * (width - len(r)) for r in rows]
    return pd.DataFrame(rows[1:], columns=rows[0])


bh_tables = [block_to_df(b) for b in blocks]
# table order on the page: 0 Endgame summary, 1 Encore summary, 2 Endgame day-wise,
# 3 Encore day-wise, 4 Endgame week-wise, 5 Endgame weekend-wise, 6 territory, 7 cinema chain
bh_summary_eg, bh_summary_enc, bh_day_eg, bh_day_enc, bh_week_eg, bh_wkend_eg, bh_terr, bh_chain = bh_tables


def tidy_bh_days(df, film_key):
    df = df.rename(columns={"Day": "label", "Date": "date_text", "Amount": "net_text", "%±": "change_text"})
    ranged = df["label"].str.contains("-")
    out_range = df[ranged].copy()
    df = df[~ranged].copy()
    df["day_no"] = df["label"].str.extract(r"Day (\d+)").astype(int)
    # '26-Apr-2019 (Fri)' -> 2019-04-26
    df["date"] = pd.to_datetime(df["date_text"].str.extract(r"(\d{2}-\w{3}-\d{4})")[0], format="%d-%b-%Y")
    df["net_cr_bh"] = df["net_text"].map(parse_inr_to_crore)
    df["film_key"] = film_key
    return df, out_range


bh_eg, bh_eg_ranges = tidy_bh_days(bh_day_eg, "AVG_ENDGAME_2019")
bh_enc, _ = tidy_bh_days(bh_day_enc, "AVG_ENCORE_2026")
log.add("bh_daywise", "days 29-56 only given as 7-day ranges ('Day 29 - Day 35')", len(bh_eg_ranges),
        "kept in weekly table only, NOT spread over days", "splitting a week evenly would invent a daily pattern")
log.add("bh_daywise", "dates as text '26-Apr-2019 (Fri)'", len(bh_eg) + len(bh_enc),
        "parsed with format %d-%b-%Y", "text dates -> datetime")
tiny = (bh_enc["net_cr_bh"] < 0.01).sum()
log.add("bh_daywise", "Encore late days below ₹0.01 Cr (e.g. '₹0.004 cr.')", int(tiny),
        "kept as is (not rounded to 0)", "small but real; rounding would create fake zero days")

# =============================================================== merge the two sources (Endgame)
release = pd.Timestamp(FILMS["AVG_ENDGAME_2019"]["release_date_india"])
eg = bh_eg[["film_key", "day_no", "date", "net_cr_bh"]].merge(
    sac[["day_no", "net_cr_sacnilk", "net_cr_english", "net_cr_hindi", "net_cr_tamil", "net_cr_telugu", "is_approx_sacnilk"]],
    on="day_no", how="outer")
eg["film_key"] = "AVG_ENDGAME_2019"
eg["date"] = release + pd.to_timedelta(eg["day_no"] - 1, unit="D")

eg["diff_cr"] = (eg["net_cr_sacnilk"] - eg["net_cr_bh"]).round(3)
disagree = eg[eg["diff_cr"].abs() > 0].copy()
disagree.to_csv(TABLES / "source_disagreements.csv", index=False)
log.add("daily_collections", "Sacnilk and Bollywood Hungama disagree on some days (e.g. Day 8: 12.00 vs 12.50)", len(disagree),
        "keep both columns; primary = Sacnilk where present", "Sacnilk gives the language split; disagreement documented, not hidden")

only_bh = eg["net_cr_sacnilk"].isna() & eg["net_cr_bh"].notna()
log.add("daily_collections", "days 22-28 missing in Sacnilk (only a Week-4 total)", int(only_bh.sum()),
        "filled from Bollywood Hungama, source column says so", "second trade source for the same day is better than a gap")

eg["net_cr"] = eg["net_cr_sacnilk"].fillna(eg["net_cr_bh"])
eg["net_source"] = eg["net_cr_sacnilk"].notna().map({True: "sacnilk", False: "bollywood_hungama"})
eg["is_approx"] = eg["is_approx_sacnilk"].fillna(False).astype(bool)

enc = bh_enc[["film_key", "day_no", "date", "net_cr_bh"]].copy()
enc["net_cr"] = enc["net_cr_bh"]
enc["net_source"] = "bollywood_hungama"
enc["is_approx"] = False

daily = pd.concat([eg, enc], ignore_index=True, sort=False)
daily["weekday"] = daily["date"].dt.day_name()
daily["is_weekend"] = daily["weekday"].isin(["Saturday", "Sunday"])
daily["week_no"] = (daily["day_no"] - 1) // 7 + 1           # Indian trade weeks run Fri-Thu
daily["cum_net_cr"] = daily.groupby("film_key")["net_cr"].cumsum()

# Opening-day value: the BH summary says 53.10 but its own day table says 53.6 (Sacnilk also 53.60).
# 53.10 was the first estimate, later revised. We use the revised day-table number.
log.add("daily_collections", "Day 1 reported as 53.10 Cr (BH summary / first Sacnilk estimate) vs 53.60 Cr (both day tables)", 1,
        "use 53.60", "day tables are the later, revised figures")

# Gross vs net: the trade tables are NET (after GST). Sacnilk's summary gives both for India:
gross_total, net_total = 445.00, 370.05
ratio = round(gross_total / net_total, 4)
daily["gross_cr_est"] = (daily["net_cr"] * ratio).round(3)
log.add("daily_collections", "only NET is given per day; we need GROSS to compare with Doomsday advance (gross)", len(daily),
        f"gross_cr_est = net x {ratio} (Sacnilk India gross 445.00 / net 370.05)",
        "single published ratio; estimate, clearly labelled _est")
log.add("daily_collections", "Sacnilk page shows two different net totals: 370.05 (summary) and 373.05 (table total)", 1,
        "report lifetime as a range (Sacnilk 370.05 / 373.05, BH 373.22), never as one exact number", "source inconsistency, documented")

cols = ["film_key", "date", "day_no", "weekday", "is_weekend", "week_no", "net_cr", "net_source", "is_approx",
        "net_cr_sacnilk", "net_cr_bh", "diff_cr", "net_cr_english", "net_cr_hindi", "net_cr_tamil", "net_cr_telugu",
        "gross_cr_est", "cum_net_cr"]
daily[cols].sort_values(["film_key", "day_no"]).to_csv(INTERIM / "daily_collections.csv", index=False)
print("daily_collections:", daily.shape)

# =============================================================== weekly table
wk_bh = bh_week_eg.rename(columns={"Day": "week_label", "Amount": "net_text"})
wk_bh["week_no"] = wk_bh["week_label"].str.extract(r"(\d+)").astype(int)
wk_bh["net_cr_bh"] = wk_bh["net_text"].map(parse_inr_to_crore)
wk_sac = sac_week[sac_week["label"].str.contains("Week")].copy()
wk_sac["week_no"] = wk_sac["label"].str.extract(r"(\d+)").astype(int)
wk_sac["net_cr_sacnilk"] = wk_sac["net_text"].map(parse_inr_to_crore)
weekly = wk_bh[["week_no", "net_cr_bh"]].merge(wk_sac[["week_no", "net_cr_sacnilk"]], on="week_no", how="left")
weekly["film_key"] = "AVG_ENDGAME_2019"

# do the days actually add up to each source's own weekly figure?
bh_day_sums = bh_eg.groupby((bh_eg["day_no"] - 1) // 7 + 1)["net_cr_bh"].sum().round(2)
sac_day_sums = sac.groupby((sac["day_no"] - 1) // 7 + 1)["net_cr_sacnilk"].sum().round(2)
weekly["bh_sum_of_days"] = weekly["week_no"].map(bh_day_sums)
weekly["sacnilk_sum_of_days"] = weekly["week_no"].map(sac_day_sums)
bad = weekly[(weekly["bh_sum_of_days"].notna()) & ((weekly["bh_sum_of_days"] - weekly["net_cr_bh"]).abs() > 0.05)]
for _, r in bad.iterrows():
    log.add("weekly_collections", f"BH week {r.week_no}: days add up to {r.bh_sum_of_days} but BH weekly table says {r.net_cr_bh}", 7,
            "kept both; lifetime total taken from published totals, shown as a range", "internal inconsistency inside one source")
log.add("weekly_collections", "Sacnilk stops at week 5; BH runs to week 8", int(weekly["net_cr_sacnilk"].isna().sum()),
        "kept NULL for Sacnilk weeks 6-8", "missing in source")
weekly.to_csv(INTERIM / "weekly_collections.csv", index=False)

# =============================================================== Doomsday advance booking (text tables)
txt = (BO / "sacnilk_doomsday_day1_advance_2026-11-21.txt").read_text(encoding="utf-8")


def section(name):
    """grab the pipe table that follows a '## name' header"""
    m = re.search(rf"## {re.escape(name)}.*?\n(.*?)(\n## |\Z)", txt, flags=re.S)
    lines = [l for l in m.group(1).splitlines() if "|" in l]
    rows = [l.split("|") for l in lines]
    return pd.DataFrame(rows[1:], columns=rows[0])


adv_parts = []
for name, level in [("Language totals", "language"), ("Top states", "state"), ("Top cities", "city")]:
    d = section(name)
    d = d.rename(columns={d.columns[0]: "area"})
    d["level"] = level
    adv_parts.append(d)
adv = pd.concat(adv_parts, ignore_index=True)

adv["gross_cr"] = adv["gross"].map(parse_inr_to_crore)
# value in brackets = without block seats
adv["gross_cr_wo_block"] = adv["gross"].str.extract(r"\[(.*?)\]")[0].map(parse_inr_to_crore)
tick_col = "tickets" if "tickets" in adv.columns else "tickets_booked"
adv["tickets"] = adv[[c for c in adv.columns if c.startswith("tickets")]].bfill(axis=1).iloc[:, 0]
adv["tickets_int"] = adv["tickets"].map(parse_indian_count)
adv["shows_int"] = adv["shows"].map(parse_indian_count)
adv["occupancy_pct"] = adv.get("occupancy", pd.Series(dtype=str)).map(parse_pct)
adv["atp_rs"] = adv.get("atp", pd.Series(dtype=str)).map(lambda x: parse_indian_count(str(x).replace("₹", "")) if pd.notna(x) else None)
adv["is_others_bucket"] = adv["area"].str.startswith("Others")
adv["film_key"] = "AVG_DOOMSDAY_2026"
adv["data_as_of"] = "2026-11-21 18:50"
log.add("advance_booking", "'Lac' and '[without block seats]' mixed into numbers ('2.97 Lac [2.61 Lac]')", len(adv),
        "two numeric columns: with and without block seats; Lac x 1e5", "type casting + keep both definitions")
log.add("advance_booking", "'Others (13 states)' / 'Others (67 cities)' buckets", int(adv["is_others_bucket"].sum()),
        "kept, flagged is_others_bucket", "needed for totals, but not a real place for ranking")
log.add("advance_booking", "occupancy missing for 'Others' rows and for language rows", int(adv["occupancy_pct"].isna().sum()),
        "kept NULL", "not published")
# derived ATP for states/cities = gross / tickets
adv["atp_rs_derived"] = (adv["gross_cr"] * 1e7 / adv["tickets_int"]).round(0)
adv["gross_per_show_lakh"] = (adv["gross_cr"] * 100 / adv["shows_int"]).round(2)

keep = ["film_key", "data_as_of", "level", "area", "gross_cr", "gross_cr_wo_block", "tickets_int", "shows_int",
        "occupancy_pct", "atp_rs", "atp_rs_derived", "gross_per_show_lakh", "is_others_bucket"]
adv[keep].to_csv(INTERIM / "advance_booking_day1.csv", index=False)
print("advance booking rows:", len(adv))

# territory + chain tables from BH (nice extra context, small)
bh_terr.to_csv(INTERIM / "endgame_territory_bh.csv", index=False)
bh_chain.to_csv(INTERIM / "endgame_chain_bh.csv", index=False)

log.save()
