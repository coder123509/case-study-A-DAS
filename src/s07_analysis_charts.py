"""
Step 7 - analysis numbers + charts (titles state the finding, computed from the data).

Charts -> outputs/charts/*.png      Numbers -> outputs/tables/key_numbers.csv
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import INTERIM, TABLES, CHARTS, TRAILER_DAY0
from utils import CleaningLog

log = CleaningLog("s07_analysis")

# ---- one look for every chart (colours = fixed per film, never by rank)
COL = {"AVG_ENDGAME_2019": "#2a78d6", "AVG_DOOMSDAY_2026": "#eb6834", "AVG_ENCORE_2026": "#1baf7a"}
NAME = {"AVG_ENDGAME_2019": "Endgame (2019)", "AVG_DOOMSDAY_2026": "Doomsday (2026)", "AVG_ENCORE_2026": "Endgame: Encore (2026)"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "lines.linewidth": 2, "axes.axisbelow": True,
})
key_numbers = []


def note(name, value, unit=""):
    key_numbers.append({"metric": name, "value": value, "unit": unit})


def save(fig, name, source):
    fig.text(0.01, 0.005, "Source: " + source, fontsize=8, color=INK2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(CHARTS / name, dpi=160)
    plt.close(fig)
    print("saved", name)


pv = pd.read_csv(INTERIM / "pageviews_daily.csv", parse_dates=["date"])
daily = pd.read_csv(INTERIM / "daily_collections_real.csv", parse_dates=["date"])

# =====================================================================================
# 1. Trailer attention curve - first 14 days, indexed to launch day (normalisation)
# =====================================================================================
win = []
for key, d0 in TRAILER_DAY0.items():
    g = pv[(pv.film_key == key) & (pv.date >= d0) & (pv.date < pd.Timestamp(d0) + pd.Timedelta(days=14))].copy()
    g["day"] = (g["date"] - pd.Timestamp(d0)).dt.days
    g["index_day0"] = 100 * g["views"] / g["views"].iloc[0]
    g["minmax"] = (g["views"] - g["views"].min()) / (g["views"].max() - g["views"].min())
    win.append(g)
win = pd.concat(win)
win.to_csv(TABLES / "trailer_window_14d.csv", index=False)
log.add("wikimedia_pageviews",
        "Endgame and Doomsday pages have very different daily scale",
        len(win),
        "added index_day0 (launch day = 100) and min-max columns for the 14-day trailer window; chart c1 plots the index",
        "normalisation: puts films of different size on one footing; the raw view counts are kept next to it")

d3 = win[win.day == 3].set_index("film_key")["index_day0"]
tot = win.groupby("film_key")["views"].sum()
half = {}
for key, g in win.groupby("film_key"):
    below = g[g["index_day0"] <= 50]
    half[key] = int(below["day"].iloc[0]) if len(below) else None
note("Endgame trailer window 14d wiki views", int(tot["AVG_ENDGAME_2019"]))
note("Doomsday trailer window 14d wiki views", int(tot["AVG_DOOMSDAY_2026"]))
note("Endgame day3 as % of day0", round(d3["AVG_ENDGAME_2019"], 1), "%")
note("Doomsday day3 as % of day0", round(d3["AVG_DOOMSDAY_2026"], 1), "%")
note("Endgame days until attention < 50% of launch day", half["AVG_ENDGAME_2019"], "days")
note("Doomsday days until attention < 50% of launch day", half["AVG_DOOMSDAY_2026"], "days")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for key, g in win.groupby("film_key"):
    axes[0].plot(g["day"], g["views"] / 1000, color=COL[key], marker="o", ms=4, label=NAME[key])
    axes[1].plot(g["day"], g["index_day0"], color=COL[key], marker="o", ms=4, label=NAME[key])
axes[0].set_title("Raw daily Wikipedia views (thousands)")
axes[1].set_title("Same data, launch day = 100")
axes[1].axhline(50, color=INK2, lw=1, ls="--")
axes[1].text(13, 52, "half of launch-day attention", ha="right", fontsize=8, color=INK2)
for ax in axes:
    ax.set_xlabel("days since first full trailer")
    ax.set_xticks(range(0, 14))
axes[0].legend(frameon=False)
fig.suptitle(f"Doomsday's trailer buzz faded faster: on day 3 it kept {d3['AVG_DOOMSDAY_2026']:.0f}% of launch-day attention, "
             f"Endgame kept {d3['AVG_ENDGAME_2019']:.0f}%", x=0.01, ha="left", fontweight="bold")
save(fig, "c1_trailer_attention_14d.png", "Wikimedia Pageviews API (en.wikipedia, user agents). Day 0 = 7-Dec-2018 / 20-Jul-2026.")

# =====================================================================================
# 2. Buzz vs box office (2 sources): Endgame release month, both series as z-scores
# =====================================================================================
eg_bo = daily[daily.film_key == "AVG_ENDGAME_2019"][["date", "day_no", "net_cr", "is_weekend"]]
eg_pv = pv[pv.film_key == "AVG_ENDGAME_2019"][["date", "views"]]
both = eg_bo.merge(eg_pv, on="date", how="inner")
both["z_net"] = (both["net_cr"] - both["net_cr"].mean()) / both["net_cr"].std()
both["z_views"] = (both["views"] - both["views"].mean()) / both["views"].std()
r_same = both["net_cr"].corr(both["views"])
r_log = np.log(both["net_cr"]).corr(np.log(both["views"]))
# does yesterday's attention say more about today's box office than today's attention?
both["views_lag1"] = both["views"].shift(1)
r_lag = both["net_cr"].corr(both["views_lag1"])
# after week 1 only (opening week dominates everything)
w2 = both[both.day_no > 7]
r_after_wk1 = w2["net_cr"].corr(w2["views"])
both.to_csv(TABLES / "endgame_buzz_vs_boxoffice_daily.csv", index=False)
note("corr(daily net, same-day wiki views) Endgame days 1-28", round(r_same, 3))
note("corr(log net, log views) Endgame days 1-28", round(r_log, 3))
note("corr(daily net, previous-day views)", round(r_lag, 3))
note("corr(daily net, same-day views) days 8-28 only", round(r_after_wk1, 3))
note("n days in correlation", len(both), "days")

pre = pv[(pv.film_key == "AVG_ENDGAME_2019") & (pv.date.between("2019-04-19", "2019-05-23"))]
fig, ax = plt.subplots(figsize=(11, 4.4))
ax.plot(both["date"], both["z_views"], color=COL["AVG_ENDGAME_2019"], marker="o", ms=4, label="Wikipedia views (z-score)")
ax.plot(both["date"], both["z_net"], color="#52514e", marker="s", ms=4, label="India net collection (z-score)")
for _, r in both[both.is_weekend].iterrows():
    ax.axvspan(r["date"] - pd.Timedelta(hours=12), r["date"] + pd.Timedelta(hours=12), color="#efeeea", zorder=0, lw=0)
ax.set_ylabel("standard deviations from 28-day mean")
ax.xaxis.set_major_locator(mdates.DayLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax.legend(frameon=False, loc="upper right")
ax.text(both["date"].iloc[10], 2.0, f"r = {r_same:.2f} over all 28 days\nr = {r_after_wk1:.2f} from day 8 on\n(shaded = weekends)",
        fontsize=9, color=INK2)
ax.set_title(f"Online attention and ticket sales moved together (r = {r_same:.2f}) - but both are driven by the release itself",
             fontsize=11.5)
save(fig, "c2_buzz_vs_boxoffice_endgame.png", "Wikimedia Pageviews API + Sacnilk / Bollywood Hungama day-wise India net. 26-Apr to 23-May-2019.")

# =====================================================================================
# 3. Inflation: nominal vs Oct-2026 rupees
# =====================================================================================
inf = pd.read_csv(TABLES / "inflation_summary.csv")
rc = [c for c in inf.columns if c.startswith("real_cr_")][0]
show = inf[inf.metric.str.contains("opening day|opening weekend|week 1|lifetime net - high")].copy()
labels = ["Opening day", "Opening weekend", "Week 1", "Lifetime (BH total)"]
x = np.arange(len(show))
fig, ax = plt.subplots(figsize=(9.5, 4.4))
b1 = ax.bar(x - 0.2, show["nominal_cr"], width=0.38, color="#9ec5f0", label="2019 rupees (as reported)")
b2 = ax.bar(x + 0.2, show[rc], width=0.38, color=COL["AVG_ENDGAME_2019"], label="Oct-2026 rupees (CPI-adjusted)")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 6, f"₹{b.get_height():.0f} Cr", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel("India net, ₹ crore")
ax.legend(frameon=False)
factor = inf["cpi_factor"].iloc[0]
note("CPI factor Apr-2019 -> Oct-2026", factor)
ax.set_title(f"In today's money Endgame's India run is worth ~₹{show[rc].iloc[-1]:.0f} Cr, not ₹373 Cr "
             f"(prices rose {100*(factor-1):.0f}% since Apr-2019)")
save(fig, "c3_inflation_effect.png", "Sacnilk / Bollywood Hungama (nominal); MoSPI CPI Combined, 2012 series linked to 2024=100 with factor 0.5267.")

# =====================================================================================
# 4. Ticket price vs CPI
# =====================================================================================
tp = pd.read_csv(TABLES / "ticket_price_vs_cpi.csv").iloc[0]
fig, ax = plt.subplots(figsize=(8, 4))
vals = [tp.atp_2019_pvr_normal_rs, tp.atp_2019_in_oct2026_rs_cpi, tp.atp_doomsday_day1_advance_rs]
labs = ["2019 PVR average\nticket (₹215)", "₹215 grown with\ngeneral CPI", "Doomsday Day-1\nadvance ATP (2026)"]
bars = ax.bar(labs, vals, color=["#9ec5f0", "#9ec5f0", COL["AVG_DOOMSDAY_2026"]], width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 12, f"₹{v:.0f}", ha="center", color=INK2)
ax.set_ylabel("₹ per ticket")
ax.set_title(f"Ticket prices outran inflation: CPI explains ₹{tp.atp_2019_in_oct2026_rs_cpi:.0f}, "
             f"Doomsday fans are paying ₹{tp.atp_doomsday_day1_advance_rs:.0f}")
ax.text(1, max(vals) * 0.92, "indicative: different scope\n(chain average vs. Day-1 advance\nincl. premium formats)",
        ha="center", fontsize=8, color=INK2)
save(fig, "c4_ticket_price_vs_cpi.png", "Business Insider India (2019 PVR ATP); MoSPI CPI; Sacnilk advance tracker 21-Nov-2026.")

# =====================================================================================
# 5. Daily decay after release: original vs re-release (velocity)
# =====================================================================================
fig, ax = plt.subplots(figsize=(10, 4.2))
decay = []
for key in ["AVG_ENDGAME_2019", "AVG_ENCORE_2026"]:
    g = daily[(daily.film_key == key) & (daily.day_no <= 21)].copy()
    g["pct_of_day1"] = 100 * g["net_cr"] / g["net_cr"].iloc[0]
    decay.append(g)
    ax.plot(g["day_no"], g["pct_of_day1"], color=COL[key], marker="o", ms=4, label=NAME[key])
decay = pd.concat(decay)
mon = decay[decay.day_no == 4].set_index("film_key")["pct_of_day1"]
wk2 = decay[decay.day_no == 8].set_index("film_key")["pct_of_day1"]
note("Endgame Monday (day 4) as % of Friday", round(mon["AVG_ENDGAME_2019"], 1), "%")
note("Encore Monday (day 4) as % of Friday", round(mon["AVG_ENCORE_2026"], 1), "%")
note("Endgame 2nd Friday as % of 1st Friday", round(wk2["AVG_ENDGAME_2019"], 1), "%")
note("Encore 2nd Friday as % of 1st Friday", round(wk2["AVG_ENCORE_2026"], 1), "%")
ax.set_xticks(range(1, 22))
ax.set_xlabel("day of release (day 1 = Friday)")
ax.set_ylabel("% of opening-day collection")
ax.legend(frameon=False)
ax.set_title(f"The Monday test: Endgame kept {mon['AVG_ENDGAME_2019']:.0f}% of its Friday, the re-release only "
             f"{mon['AVG_ENCORE_2026']:.0f}% - fan-driven demand is front-loaded")
save(fig, "c5_daily_decay_original_vs_rerelease.png", "Sacnilk / Bollywood Hungama day-wise India net (normalised to day 1).")

# =====================================================================================
# 6. Review themes (unstructured -> counts)
# =====================================================================================
th = pd.read_csv(TABLES / "theme_summary.csv").sort_values("share_of_reviews_pct")
pretty = {"story_plot": "story / plot", "length_pacing": "length / pacing", "emotion": "emotion",
          "action_vfx": "action / VFX", "characters_acting": "characters / acting",
          "extra_scenes_encore": "extra scenes (Encore)", "price_value": "price / value for money",
          "format_experience": "format (IMAX, 4DX...)", "doomsday_hype": "Doomsday anticipation"}
fig, ax = plt.subplots(figsize=(10, 4.6))
colors = ["#e34948" if t == "price_value" else "#9ec5f0" for t in th["theme"]]
bars = ax.barh([pretty[t] for t in th["theme"]], th["share_of_reviews_pct"], color=colors, height=0.6)
for b, (_, r) in zip(bars, th.iterrows()):
    ax.text(b.get_width() + 0.4, b.get_y() + b.get_height() / 2,
            f"avg {r.avg_rating_10_with_theme:.1f}/10  (n={r.n_reviews})", va="center", fontsize=8.5, color=INK2)
ax.set_xlabel("% of reviews mentioning the theme")
pv_row = th.set_index("theme").loc["price_value"]
ax.set_title(f"Value for money is the one complaint that sinks ratings: {pv_row.avg_rating_10_with_theme:.1f}/10 "
             f"vs {pv_row.avg_rating_10_without:.1f} for all other reviews")
ax.set_xlim(0, th["share_of_reviews_pct"].max() + 12)
save(fig, "c6_review_themes.png", "Rotten Tomatoes audience reviews (n=140, Oct-Nov 2026, Encore period) + 5 public IMDb reviews. Keyword dictionary in s05.")

# =====================================================================================
# 7. Doomsday advance booking by state (gross per show vs occupancy)
# =====================================================================================
adv = pd.read_csv(INTERIM / "advance_booking_day1.csv")
st = adv[(adv.level == "state") & (~adv.is_others_bucket)].copy()
allindia = adv[(adv.level == "language") & (adv.area == "All India")].iloc[0]
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.scatter(st["occupancy_pct"], st["gross_per_show_lakh"], s=st["shows_int"] / 2.5, color=COL["AVG_DOOMSDAY_2026"],
           alpha=0.85, edgecolor="#fcfcfb", linewidth=2)
for _, r in st.iterrows():
    ax.annotate(r["area"], (r["occupancy_pct"], r["gross_per_show_lakh"]), xytext=(6, 4), textcoords="offset points",
                fontsize=8.5, color=INK2)
ax.axhline(allindia["gross_per_show_lakh"], color=INK2, ls="--", lw=1)
ax.text(st["occupancy_pct"].max(), allindia["gross_per_show_lakh"] + 0.03, "all-India gross per show", ha="right", fontsize=8, color=INK2)
ax.set_xlabel("Day-1 advance occupancy (%)")
ax.set_ylabel("Day-1 advance gross per show (₹ lakh)")
south_hot = st[st.occupancy_pct >= 60]["area"].tolist()
ax.set_title(f"Where to add shows first: {', '.join(south_hot)} are already 60%+ full, 26 days out")
save(fig, "c7_doomsday_advance_by_state.png", "Sacnilk advance-booking tracker, data as of 21-Nov-2026 18:50 IST (bubble size = shows).")

log.add("box_office + wikimedia_pageviews",
        "views and net collection cannot share one axis",
        len(both),
        "z-score of each series over the same 28 days for chart c2 (correlation r is unchanged by this step)",
        "normalisation: one footing for two units, no dual axis")
compared = daily[daily.film_key.isin(["AVG_ENDGAME_2019", "AVG_ENCORE_2026"])]
log.add("daily_collections",
        "Endgame (2019) and the Encore re-release (2026) differ about 10x in rupees, so their decay curves cannot be compared raw",
        int(len(compared)),
        "each day as % of that film's own day-1 net (chart c5, Monday test)",
        "normalisation: compares shape of decay, not size; the rupee amounts are compared separately after the CPI step")
log.save()

pd.DataFrame(key_numbers).to_csv(TABLES / "key_numbers.csv", index=False)
print(pd.DataFrame(key_numbers).to_string())
