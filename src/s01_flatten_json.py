"""
Step 1 - flatten the three JSON sources into flat tables (pd.json_normalize).

  data/raw/wikimedia_pageviews/*.json   -> data/interim/pageviews_daily.csv
  data/raw/wikidata/*.json              -> data/interim/film_metadata.csv
  data/raw/youtube/*.json               -> data/interim/youtube_videos.csv
"""
import json
import pandas as pd

from config import RAW, INTERIM
from utils import CleaningLog, match_film

log = CleaningLog("s01_flatten_json")


# ---------------------------------------------------------------- pageviews
frames = []
for f in sorted((RAW / "wikimedia_pageviews").glob("*.json")):
    with open(f, encoding="utf-8") as fh:
        js = json.load(fh)
    df = pd.json_normalize(js, record_path="items")
    df["source_file"] = f.name
    frames.append(df)
pv = pd.concat(frames, ignore_index=True)

# timestamp comes as '2019042600' (YYYYMMDDHH) -> real date
pv["date"] = pd.to_datetime(pv["timestamp"].str[:8], format="%Y%m%d")
pv["views"] = pv["views"].astype("int64")
pv["film_key"] = pv["article"].map(lambda a: match_film(a.replace("_", " "))[0])

# The 'Avengers:_Endgame' article only got that name on 7 Dec 2018 (title reveal).
# Before that the page was a redirect stub -> views of 1-2 per day. Those are real
# numbers but not "attention to the film", so we flag them instead of deleting.
pv["pre_title_reveal"] = (pv["film_key"] == "AVG_ENDGAME_2019") & (pv["date"] < "2018-12-07")
n = int(pv["pre_title_reveal"].sum())
log.add("wikimedia_pageviews", "Endgame article did not exist under this title before 2018-12-07 (views = 1-2/day)",
        n, "kept, flagged pre_title_reveal=True, excluded from the trailer window",
        "the 'Avengers: Endgame' title was revealed with the first trailer; earlier traffic went to another page name")

# check for gaps in the daily series (missing days would break the 14-day window)
for key, g in pv.groupby("film_key"):
    full = pd.date_range(g["date"].min(), g["date"].max(), freq="D")
    missing = len(full) - g["date"].nunique()
    log.add("wikimedia_pageviews", f"{key}: missing calendar days in daily series", missing,
            "none to fix" if missing == 0 else "left as NaN (not filled)",
            "the API returns one row per day; we verify instead of assuming")

pv = pv[["film_key", "project", "article", "access", "agent", "date", "views", "pre_title_reveal"]]
pv.to_csv(INTERIM / "pageviews_daily.csv", index=False)
print("pageviews:", pv.shape)


# ---------------------------------------------------------------- wikidata metadata
with open(RAW / "wikidata" / "wikidata_film_metadata.json", encoding="utf-8") as fh:
    wd = json.load(fh)
meta = pd.json_normalize(wd["results"]["bindings"])
# json_normalize gives columns like 'filmLabel.value', 'duration.datatype' ... keep the values only
meta = meta[[c for c in meta.columns if c.endswith(".value")]]
meta.columns = [c.replace(".value", "") for c in meta.columns]

# Doomsday has no English label on Wikidata (only a 'mul' label), so the label service returned the QID
bad_label = meta["filmLabel"].str.match(r"^Q\d+$")
log.add("wikidata", "filmLabel came back as a QID (no English label on Wikidata)", int(bad_label.sum()),
        "title filled from our film key table via the QID", "film-name matching: QID is a reliable key")

meta["film_key"] = meta.apply(lambda r: match_film(r["filmLabel"])[0], axis=1)
meta["runtime_min"] = pd.to_numeric(meta.get("duration"), errors="coerce")
log.add("wikidata", "runtime missing for Doomsday (unreleased film)", int(meta["runtime_min"].isna().sum()),
        "kept as NULL", "runtime is not public yet; filling it would be invention")

# 'publicationDates' looks like '2019-04-26T00:00:00Z@United States|2019-04-26T00:00:00Z@India'
def pick_india_date(s):
    parts = [p.split("@") for p in str(s).split("|")]
    india = [d for d, place in parts if place == "India"]
    return india[0][:10] if india else None

meta["release_date_india_wikidata"] = meta["publicationDates"].map(pick_india_date)
log.add("wikidata", "no India-specific release date for Doomsday on Wikidata", int(meta["release_date_india_wikidata"].isna().sum()),
        "use 17-Dec-2026 from ThePrint/Sacnilk in the films table, keep Wikidata value NULL",
        "Wikidata only lists the US date (18 Dec); India opens a day earlier")
meta.to_csv(INTERIM / "film_metadata.csv", index=False)
print("metadata:", meta.shape)


# ---------------------------------------------------------------- youtube
with open(RAW / "youtube" / "youtube_trailers_snapshot_2026-11-21.json", encoding="utf-8") as fh:
    yt_js = json.load(fh)
yt = pd.json_normalize(yt_js["items"])  # -> snippet.title, statistics.viewCount, ...
yt.columns = [c.split(".")[-1] for c in yt.columns]
yt = yt.rename(columns={"id": "video_id"})

# type casting: counts arrive as strings with commas ("3,377,553")
for col in ["viewCount", "likeCount", "commentCount"]:
    yt[col] = pd.to_numeric(yt[col].astype("string").str.replace(",", ""), errors="coerce").astype("Int64")
log.add("youtube", "view/like counts stored as text with thousands separators", len(yt),
        "stripped commas, cast to Int64", "needed for arithmetic and normalisation")
log.add("youtube", "commentCount not available from the watch page", int(yt["commentCount"].isna().sum()),
        "kept as NULL (re-run src/collect/youtube_api_collector.py with an API key to fill it)",
        "a missing count is not zero")

yt["published_at"] = pd.to_datetime(yt["publishedAt"], utc=True)
yt["durationSeconds"] = yt["durationSeconds"].astype(int)
yt["snapshot_taken_at"] = yt_js["collection"]["snapshot_taken_at"]
yt["days_online_at_snapshot"] = (pd.Timestamp(yt_js["collection"]["snapshot_taken_at"]).tz_convert("UTC")
                                 - yt["published_at"]).dt.days
matches = yt.apply(lambda r: match_film(r["title"], r["published_at"].year), axis=1)
yt["film_key"] = [m[0] for m in matches]
yt["match_method"] = [m[1] for m in matches]
yt["language"] = yt["title"].str.contains("Hindi", case=False).map({True: "Hindi", False: "English"})
log.add("youtube", "Dec-2018 Endgame trailers are titled 'Avengers - Official Trailer' (no 'Endgame')",
        int((yt["match_method"] == "rule:untitled-avengers-trailer-2018").sum()),
        "matched by rule using the publish year", "the title 'Endgame' was revealed inside that trailer")

yt = yt[["video_id", "film_key", "match_method", "title", "channelTitle", "language", "published_at",
         "durationSeconds", "viewCount", "likeCount", "commentCount", "days_online_at_snapshot", "snapshot_taken_at"]]
yt.to_csv(INTERIM / "youtube_videos.csv", index=False)
print("youtube:", yt.shape)

log.save()
