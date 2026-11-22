"""
Step 8 - the "Release Day Radar": turn what we learned from Endgame (2019) and the
Encore re-release (2026) into simple checks the Head of Distribution can run for Doomsday.

This is decision SUPPORT, not a prediction model: 1 historical film is not enough to fit one.
Every threshold below comes from a number we measured, and the file says which one.

Outputs: outputs/tables/radar_checklist.csv, outputs/tables/doomsday_opening_scenarios.csv
"""
import pandas as pd

from config import INTERIM, RAW, TABLES
from utils import parse_inr_to_crore

daily = pd.read_csv(INTERIM / "daily_collections_real.csv", parse_dates=["date"])
pv = pd.read_csv(INTERIM / "pageviews_daily.csv", parse_dates=["date"])
adv = pd.read_csv(INTERIM / "advance_booking_day1.csv")
snaps = pd.read_csv(RAW / "manual_compiled" / "advance_booking_snapshots.csv")
themes = pd.read_csv(TABLES / "theme_summary.csv").set_index("theme")
kn = pd.read_csv(TABLES / "key_numbers.csv").set_index("metric")["value"]

eg = daily[daily.film_key == "AVG_ENDGAME_2019"].set_index("day_no")
enc = daily[daily.film_key == "AVG_ENCORE_2026"].set_index("day_no")
f = eg["cpi_factor_to_target"].iloc[0]

# ---------------------------------------------------------------- benchmarks we measured
eg_day1_net = eg.loc[1, "net_cr"]
eg_day1_gross_real = eg.loc[1, "gross_cr_est"] * f
eg_mon_hold = eg.loc[4, "net_cr"] / eg.loc[1, "net_cr"]
enc_mon_hold = enc.loc[4, "net_cr"] / enc.loc[1, "net_cr"]
eg_wk2_fri = eg.loc[8, "net_cr"] / eg.loc[1, "net_cr"]
eg_wkend2_vs_1 = eg.loc[8:10, "net_cr"].sum() / eg.loc[1:3, "net_cr"].sum()
enc_wkend2_vs_1 = enc.loc[8:10, "net_cr"].sum() / enc.loc[1:3, "net_cr"].sum()

eg_pv = pv[pv.film_key == "AVG_ENDGAME_2019"].set_index("date")["views"]
release_vs_trailer = eg_pv[pd.Timestamp("2019-04-26")] / eg_pv[pd.Timestamp("2018-12-07")]

ai = adv[(adv.level == "language") & (adv.area == "All India")].iloc[0]
doom_adv_gross = ai["gross_cr"]
share_of_eg_day1 = doom_adv_gross / eg_day1_gross_real

# advance velocity between the two Sacnilk tracker snapshots
a = snaps[snaps.snapshot_label == "tracker snapshot A"].iloc[0]
b = snaps[snaps.snapshot_label == "tracker snapshot B"].iloc[0]
hours = (pd.Timestamp(b.data_as_of_ist) - pd.Timestamp(a.data_as_of_ist)).total_seconds() / 3600
adv_per_day = (parse_inr_to_crore(b.day1_gross) - parse_inr_to_crore(a.day1_gross)) / hours * 24

hot_states = adv[(adv.level == "state") & (~adv.is_others_bucket) & (adv.occupancy_pct >= 60)]["area"].tolist()
price_share = themes.loc["price_value", "share_of_reviews_pct"]
price_rating = themes.loc["price_value", "avg_rating_10_with_theme"]

# ---------------------------------------------------------------- checklist
rows = [
    {"when": "Before release (now)", "signal": "Day-1 advance gross vs Endgame Day-1 gross in today's money",
     "doomsday_now": f"₹{doom_adv_gross:.2f} Cr = {100*share_of_eg_day1:.0f}% of ₹{eg_day1_gross_real:.1f} Cr",
     "benchmark_source": "Endgame Day-1 net 53.60 x gross/net 1.2025 x CPI 1.48",
     "rule": "Keep the show count growing while the advance keeps adding; re-check weekly",
     "action_if_triggered": "If advance passes 50% of benchmark >7 days out: lock extra early-morning/midnight shows (Endgame ran 24x7 in 2019)"},
    {"when": "Before release (now)", "signal": "Advance velocity (Sacnilk tracker, Day-1 gross per day)",
     "doomsday_now": f"+₹{adv_per_day:.2f} Cr/day over the last {hours:.0f} h",
     "benchmark_source": "two tracker snapshots, 19-Nov and 21-Nov-2026",
     "rule": "A falling daily add = demand already captured by fans, not growing",
     "action_if_triggered": "If daily add drops below half of today's pace before release week: hold promo spend for release week instead of now"},
    {"when": "Before release (now)", "signal": "States with Day-1 occupancy >= 60%",
     "doomsday_now": ", ".join(hot_states) if hot_states else "none",
     "benchmark_source": "Sacnilk state table",
     "rule": "High occupancy with few shows = under-supplied market",
     "action_if_triggered": "Add regional-language / standard 2D shows there first (lower-price markets: derived ATP about ₹260-₹390 per ticket there vs ₹699 all-India)"},
    {"when": "Release weekend", "signal": "Wikipedia attention on release day vs trailer day",
     "doomsday_now": "to be measured on 17-Dec-2026",
     "benchmark_source": f"Endgame: release-day views were {release_vs_trailer:.1f}x trailer-day views",
     "rule": "Attention moves with collections in the same days (r = %.2f), so it confirms, it does not predict" % kn["corr(daily net, same-day wiki views) Endgame days 1-28"],
     "action_if_triggered": "Use as a same-day sanity check on trade estimates, not as a forecast"},
    {"when": "First Monday (21-Dec = day 5, Doomsday opens on a Thursday)", "signal": "Monday collection as % of opening day",
     "doomsday_now": "to be measured on 21-Dec-2026",
     "benchmark_source": f"Endgame {100*eg_mon_hold:.0f}% (original) vs Encore {100*enc_mon_hold:.0f}% (fan-only re-release)",
     "rule": f">= {100*eg_mon_hold:.0f}%: broad audience, legs like Endgame. <= {100*enc_mon_hold:.0f}%: fan rush, front-loaded",
     "action_if_triggered": "Above Endgame line: keep screens in week 2 and add in hot states. Near Encore line: cut 25-30% of week-2 shows, move them to holdovers"},
    {"when": "Second weekend (25-27 Dec)", "signal": "2nd weekend vs 1st weekend (Fri-Sun)",
     "doomsday_now": "to be measured on 27-Dec-2026",
     "benchmark_source": f"Endgame 2nd Fri {100*eg_wk2_fri:.0f}%, weekend-2/weekend-1 {100*eg_wkend2_vs_1:.0f}% (Encore {100*enc_wkend2_vs_1:.0f}%)",
     "rule": "Christmas/New-Year holidays fall in week 2 for Doomsday (Endgame had none) - expect a better hold, compare carefully",
     "action_if_triggered": f"If weekend-2 < {100*eg_wkend2_vs_1:.0f}% of weekend-1 even with holidays: word of mouth is weak, stop incremental promo"},
    {"when": "First week", "signal": "Share of audience reviews complaining about price / value",
     "doomsday_now": "to be measured (re-run s03-s05 on new reviews)",
     "benchmark_source": f"Encore period: {price_share:.0f}% of reviews, avg {price_rating:.1f}/10 vs ~8.9 for the rest",
     "rule": "Price complaints drag ratings far more than any other theme",
     "action_if_triggered": "If > 10% of reviews: shift shows from premium (₹766 ATP English) to standard formats; promote value shows"},
]
radar = pd.DataFrame(rows)
radar.to_csv(TABLES / "radar_checklist.csv", index=False)
print(radar[["when", "signal", "doomsday_now"]].to_string())

# ---------------------------------------------------------------- cautious opening-day scenarios (India NET, ₹ Cr)
# national-chain (PVR/INOX/Cinepolis) Day-1 advance, both from Sacnilk (see advance_booking_snapshots.csv)
nc_eg_final_adv = parse_inr_to_crore(snaps.loc[snaps.snapshot_label == "benchmark 2019", "day1_gross"].dropna().iloc[0])
nc_doom_adv_now = parse_inr_to_crore(snaps.loc[snaps.snapshot_label == "national chains 19-Nov", "day1_gross"].iloc[0])
mult = eg_day1_net / nc_eg_final_adv
scen = pd.DataFrame([
    {"scenario": "Low: same nominal rupees as Endgame (= about 32% less in real terms)",
     "day1_net_cr": round(eg_day1_net, 1), "assumption": "2019 rupees, no inflation"},
    {"scenario": "Mid: same real money as Endgame (CPI-adjusted)",
     "day1_net_cr": round(eg_day1_net * f, 1), "assumption": f"Endgame Day-1 x CPI factor {f:.3f}"},
    {"scenario": "High: Endgame's advance-to-Day-1 multiple applied to Doomsday's national-chain advance",
     "day1_net_cr": round(nc_doom_adv_now * mult, 1),
     "assumption": f"Endgame Day-1 net / its final national-chain advance = {mult:.2f}; Doomsday NC advance ₹14.5 Cr (19-Nov, 28 days out). "
                   "Upper reference only: 2026 audiences book far more in advance than in 2019, so the multiple is probably smaller."},
])
scen.to_csv(TABLES / "doomsday_opening_scenarios.csv", index=False)
print(scen.to_string())
