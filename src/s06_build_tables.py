"""
Step 6 - final relational tables (one CSV per MySQL table) in data/processed/.

    films  1---*  daily_collections  *---1  cpi_monthly   (via collection_month)
    films  1---*  wiki_pageviews
    films  1---*  youtube_videos
    films  1---*  reviews
    films  1---*  advance_booking
    films  1---1  release_schedule

The same CSVs are loaded into MySQL by sql/load_data.sql (see README).
"""
import pandas as pd

from config import RAW, INTERIM, PROCESSED, FILMS
from utils import CleaningLog

log = CleaningLog("s06_build_tables")

# ------------------------------------------------------------------ films
meta = pd.read_csv(INTERIM / "film_metadata.csv").set_index("film_key")
films = []
for i, (key, f) in enumerate(FILMS.items(), start=1):
    m = meta.loc[key] if key in meta.index else None
    genres = m["genres"] if m is not None else meta.loc["AVG_ENDGAME_2019", "genres"]
    films.append({
        "film_id": i,
        "film_key": key,
        "title": f["title"],
        "release_date_india": f["release_date_india"],
        "release_type": f["release_type"],
        "parent_film_id": 1 if key == "AVG_ENCORE_2026" else None,
        "genres": genres,
        "runtime_min": (m["runtime_min"] if m is not None else None),
        "original_language": "English",
        "imdb_id": f["imdb_id"],
        "wikidata_id": f["wikidata_id"],
        "tmdb_id": f["tmdb_id"],
    })
films = pd.DataFrame(films)
films["parent_film_id"] = films["parent_film_id"].astype("Int64")
films["runtime_min"] = pd.to_numeric(films["runtime_min"]).astype("Int64")
log.add("films", "Encore has no Wikidata entry of its own", 1,
        "genres copied from the parent film (same film + extra scenes), parent_film_id = 1", "re-release of the same title")
key2id = dict(zip(films["film_key"], films["film_id"]))
films.to_csv(PROCESSED / "films.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ cpi_monthly
cpi = pd.read_csv(INTERIM / "cpi_monthly.csv", parse_dates=["month"])
cpi["month"] = cpi["month"].dt.strftime("%Y-%m-01")
cpi.to_csv(PROCESSED / "cpi_monthly.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ daily_collections
d = pd.read_csv(INTERIM / "daily_collections_real.csv", parse_dates=["date"])
d["film_id"] = d["film_key"].map(key2id)
d["collection_month"] = d["date"].dt.strftime("%Y-%m-01")
# Nov-2026 Encore days have no CPI row yet -> FK would break. Point them at NULL month.
no_cpi = ~d["collection_month"].isin(cpi["month"])
d.loc[no_cpi, "collection_month"] = None
log.add("daily_collections", "Nov-2026 rows have no CPI month row (not published yet)", int(no_cpi.sum()),
        "collection_month = NULL for those rows (FK allows NULL)", "keeps referential integrity")
dc = d.rename(columns={"date": "collection_date"})[[
    "film_id", "collection_date", "day_no", "weekday", "is_weekend", "week_no", "net_cr", "net_source", "is_approx",
    "net_cr_sacnilk", "net_cr_bh", "net_cr_english", "net_cr_hindi", "net_cr_tamil", "net_cr_telugu",
    "gross_cr_est", "collection_month", "cpi_factor_to_target", "net_cr_real"]]
dc["collection_date"] = dc["collection_date"].dt.strftime("%Y-%m-%d")
for b in ["is_weekend", "is_approx"]:
    dc[b] = dc[b].astype(int)
dc.to_csv(PROCESSED / "daily_collections.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ wiki_pageviews
pv = pd.read_csv(INTERIM / "pageviews_daily.csv", parse_dates=["date"])
pv["film_id"] = pv["film_key"].map(key2id)
pv = pv.rename(columns={"date": "view_date"})
pv["view_date"] = pv["view_date"].dt.strftime("%Y-%m-%d")
pv["pre_title_reveal"] = pv["pre_title_reveal"].astype(int)
pv[["film_id", "view_date", "project", "article", "views", "pre_title_reveal"]].to_csv(PROCESSED / "wiki_pageviews.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ youtube_videos
yt = pd.read_csv(INTERIM / "youtube_videos.csv")
yt["film_id"] = yt["film_key"].map(key2id)
yt["published_at"] = pd.to_datetime(yt["published_at"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S")
yt["snapshot_taken_at"] = pd.to_datetime(yt["snapshot_taken_at"]).dt.tz_convert("UTC").dt.strftime("%Y-%m-%d %H:%M:%S")
yt = yt.rename(columns={"channelTitle": "channel", "durationSeconds": "duration_sec", "viewCount": "view_count",
                        "likeCount": "like_count", "commentCount": "comment_count"})
yt[["video_id", "film_id", "title", "channel", "language", "published_at", "duration_sec", "view_count",
    "like_count", "comment_count", "days_online_at_snapshot", "snapshot_taken_at"]].to_csv(PROCESSED / "youtube_videos.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ reviews
r = pd.read_csv(INTERIM / "reviews_scored.csv", parse_dates=["review_date"])
r["film_id"] = r["film_key"].map(key2id)
r["review_date"] = r["review_date"].dt.strftime("%Y-%m-%d")
theme_cols = [c for c in r.columns if c.startswith("theme_")]
for c in theme_cols + ["is_short", "is_text_duplicate"]:
    r[c] = r[c].astype(int)
r["text"] = r["text"].astype(str).str.replace("\r", "", regex=False)
r["verified"] = r["verified"].map({True: 1, False: 0, "True": 1, "False": 0})
r[["review_id", "film_id", "source", "viewing_context", "review_date", "rating_10", "rating_label", "verified", "lang",
   "n_words", "is_short", "is_text_duplicate", "vader_compound", "model_pos_prob"] + theme_cols + ["text"]].to_csv(
    PROCESSED / "reviews.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ advance_booking
adv = pd.read_csv(INTERIM / "advance_booking_day1.csv")
adv["film_id"] = adv["film_key"].map(key2id)
adv["snapshot_at"] = pd.to_datetime(adv["data_as_of"]).dt.strftime("%Y-%m-%d %H:%M:%S")
adv["show_date"] = "2026-12-17"
adv["is_others_bucket"] = adv["is_others_bucket"].astype(int)
adv.insert(0, "booking_row_id", range(1, len(adv) + 1))
adv[["booking_row_id", "film_id", "snapshot_at", "show_date", "level", "area", "gross_cr", "gross_cr_wo_block",
     "tickets_int", "shows_int", "occupancy_pct", "atp_rs", "atp_rs_derived", "is_others_bucket"]].rename(
    columns={"tickets_int": "tickets", "shows_int": "shows"}).to_csv(PROCESSED / "advance_booking.csv", index=False, lineterminator="\n")

# ------------------------------------------------------------------ release_schedule
rs = pd.read_csv(RAW / "manual_compiled" / "release_timing.csv")
title2key = {v["title"]: k for k, v in FILMS.items()}
rs["film_id"] = rs["film"].map(title2key).map(key2id)
rs[["film_id", "india_release_date", "weekday", "other_release_note", "first_show_note", "show_screen_note",
    "source_name", "source_url"]].to_csv(PROCESSED / "release_schedule.csv", index=False, lineterminator="\n")

for f in sorted(PROCESSED.glob("*.csv")):
    print(f"{f.name:28s} {sum(1 for _ in open(f, encoding='utf-8')) - 1:>5} rows")
log.save()
