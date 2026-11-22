"""
Quick check of sql/queries.sql WITHOUT a MySQL server.

Loads data/processed/*.csv into an in-memory SQLite database, translates the few
MySQL-only bits (DATEDIFF, DATE_ADD, DATE 'literal'), runs every query, prints a
short preview, and stores the full result.

Stored files
  outputs/tables/sql/q1_....csv … q9_....csv     one file per query, every row
  outputs/tables/sql/query_results.txt           the full terminal printout
  outputs/charts/sql/q1_....png, q3_....png, q9_....png
      only the results that are not already charts c1–c7

    python sql/check_queries_sqlite.py
"""
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "outputs" / "tables" / "sql"
CHARTS = ROOT / "outputs" / "charts" / "sql"
TABLES.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

FILES = {
    "Q1": "q1_weekly_net.csv",
    "Q2": "q2_opening_weekend.csv",
    "Q3": "q3_source_disagreement.csv",
    "Q4": "q4_trailer_decay.csv",
    "Q5": "q5_youtube_by_language.csv",
    "Q6": "q6_review_themes.csv",
    "Q7": "q7_advance_gross_per_show.csv",
    "Q8": "q8_inflation_by_month.csv",
    "Q9": "q9_sentiment_vs_stars.csv",
}

con = sqlite3.connect(":memory:")
for f in sorted((ROOT / "data" / "processed").glob("*.csv")):
    pd.read_csv(f).to_sql(f.stem, con, index=False)

sql = (ROOT / "sql" / "queries.sql").read_text(encoding="utf-8")
sql = re.sub(r"^USE .*?;", "", sql, flags=re.M)


def to_sqlite(q):
    q = re.sub(r"DATE '(\d{4}-\d{2}-\d{2})'", r"'\1'", q)
    q = re.sub(r"DATEDIFF\(([^,]+),\s*([^)]+)\)", r"CAST(julianday(\1) - julianday(\2) AS INT)", q)
    q = re.sub(r"DATE_ADD\(([^,]+),\s*INTERVAL (\d+) DAY\)", r"date(\1, '+\2 day')", q)
    return q


frames = {}
lines = []
ok = 0
blocks = re.split(r"\n(?=-- Q\d)", sql)
for b in blocks:
    m = re.match(r"-- (Q\d+)[^\n]*", b.strip())
    if not m:
        continue
    qid = m.group(1)
    q = to_sqlite(b.strip())
    try:
        res = pd.read_sql_query(q, con)
    except Exception as e:
        block = f"\n=== {m.group(0)}\nFAILED: {e}"
        print(block)
        lines.append(block)
        continue
    ok += 1
    frames[qid] = res
    path = TABLES / FILES[qid]
    res.to_csv(path, index=False)
    preview = res.head(12).to_string(index=False)
    block = f"\n=== {m.group(0)}\n{res.to_string(index=False)}\n({len(res)} rows)\nstored: {path.relative_to(ROOT)}"
    lines.append(block)
    print(f"\n=== {m.group(0)}\n{preview}\n({len(res)} rows) -> {path.relative_to(ROOT)}")

transcript = TABLES / "query_results.txt"
transcript.write_text("\n".join(lines).strip() + f"\n\n{ok} queries ran OK\n", encoding="utf-8")
print(f"\n{ok} queries ran OK")
print(f"full printout: {transcript.relative_to(ROOT)}")


def plot_new_results():
    """Charts for query results that c1–c7 do not already show."""
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "outputs" / ".mplconfig"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    ink, ink2, grid = "#0b0b0b", "#52514e", "#e4e3df"
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": grid,
        "axes.labelcolor": ink2, "xtick.color": ink2, "ytick.color": ink2, "text.color": ink,
        "axes.grid": True, "grid.color": grid, "grid.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.axisbelow": True,
    })

    def save(fig, name, source):
        fig.text(0.01, 0.005, "Source: " + source, fontsize=8, color=ink2, ha="left", va="bottom")
        fig.tight_layout(rect=(0, 0.04, 1, 1))
        fig.savefig(CHARTS / name, dpi=160)
        plt.close(fig)
        print("saved", (CHARTS / name).relative_to(ROOT))

    # Q1. Week-by-week nominal vs today's rupees. c3 only shows four Endgame totals.
    q1 = frames["Q1"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, title, color in (
        (axes[0], "Avengers: Endgame", "#2a78d6"),
        (axes[1], "Avengers Endgame: Encore", "#1baf7a"),
    ):
        g = q1[q1.title == title]
        x = np.arange(len(g))
        ax.bar(x - 0.18, g.net_cr_nominal, width=0.36, color="#c5c4c0", label="Nominal rupees")
        ax.bar(x + 0.18, g.net_cr_oct2026_prices, width=0.36, color=color, label="Oct-2026 rupees")
        ax.set_xticks(x)
        ax.set_xticklabels([f"W{int(w)}" for w in g.week_no])
        ax.set_ylabel("India net, ₹ crore")
        ax.legend(frameon=False, fontsize=8)
    axes[0].set_title("Endgame, 2019 rupees vs today")
    axes[1].set_title("Encore, already in 2026 prices")
    fig.suptitle("Endgame's weeks grow by about 1.48× in today's rupees; the re-release barely moves",
                 x=0.01, ha="left", fontweight="bold")
    save(fig, "q1_weekly_nominal_vs_real.png", "sql/queries.sql Q1 on data/processed/daily_collections.csv, CPI-adjusted net.")

    # Q3. Signed gap hides week 2. c3 and the cleaning log do not show this column.
    q3 = frames["Q3"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(q3))
    ax.bar(x - 0.18, q3.signed_gap_cr, width=0.36, color="#9ec5f0", label="Signed gap (Sacnilk − BH)")
    ax.bar(x + 0.18, q3.absolute_gap_cr, width=0.36, color="#e34948", label="Absolute gap")
    ax.axhline(0, color=ink2, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Week {int(w)}" for w in q3.week_no])
    ax.set_ylabel("₹ crore")
    ax.legend(frameon=False)
    ax.set_title("Week 2 disagrees by ₹1.00 Cr\nThe signed gap is ₹0 because the two days cancel")
    save(fig, "q3_signed_vs_absolute_gap.png", "sql/queries.sql Q3. Days where both Sacnilk and Bollywood Hungama published a net.")

    # Q9. Model probability by theme is not on c6, which shows star ratings only.
    q9 = frames["Q9"]
    themes = q9[q9.theme != "ALL_ENGLISH"].sort_values("avg_model_pos_prob")
    overall = q9[q9.theme == "ALL_ENGLISH"].iloc[0]
    pretty = {
        "story_plot": "story / plot", "length_pacing": "length / pacing", "emotion": "emotion",
        "action_vfx": "action / VFX", "characters_acting": "characters / acting",
        "extra_scenes_encore": "extra scenes (Encore)", "price_value": "price / value for money",
        "format_experience": "format (IMAX, 4DX...)", "doomsday_hype": "Doomsday anticipation",
    }
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = ["#e34948" if t == "price_value" else "#9ec5f0" for t in themes.theme]
    bars = ax.barh([pretty[t] for t in themes.theme], themes.avg_model_pos_prob, color=colors, height=0.62)
    for b, (_, r) in zip(bars, themes.iterrows()):
        ax.text(b.get_width() + 0.01, b.get_y() + b.get_height() / 2,
                f"{r.avg_model_pos_prob:.2f}   agrees {r.agree_pct:.0f}%  (n={int(r.n_compared)})",
                va="center", fontsize=8.5, color=ink2)
    ax.set_xlabel("Average TF-IDF probability that the review is positive")
    ax.set_xlim(0, 1.35)
    ax.axvline(0.5, color=ink2, lw=0.8, ls="--")
    ax.set_title(f"The model matches the stars on {overall.agree_pct:.1f}% of clear reviews\n"
                 f"Price mentions are the only theme near 0.5")
    save(fig, "q9_model_vs_stars.png", "sql/queries.sql Q9. English reviews with a model score. Agreement drops mixed labels, same rule as sentiment_model_eval.csv.")


if ok == len(FILES):
    plot_new_results()
else:
    raise SystemExit("skipped charts because a query failed")
