"""
Paths and a few project-wide constants.
Everything else in src/ imports from here, so if you move folders, change it here only.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
CHARTS = ROOT / "outputs" / "charts"
TABLES = ROOT / "outputs" / "tables"
SQL_DIR = ROOT / "sql"

for p in (INTERIM, PROCESSED, CHARTS, TABLES):
    p.mkdir(parents=True, exist_ok=True)

# Date we pulled the raw files (used to turn "6 days ago" into a real date)
ACCESS_DATE = "2026-11-21"

# ---- film keys -------------------------------------------------------------
# One clean key per film. Every source spells the title differently, so
# utils.match_film() maps whatever we see onto one of these.
FILMS = {
    "AVG_ENDGAME_2019": {
        "title": "Avengers: Endgame",
        "release_date_india": "2019-04-26",
        "imdb_id": "tt4154796",
        "wikidata_id": "Q23781155",
        "tmdb_id": "299534",
        "release_type": "original",
    },
    "AVG_ENCORE_2026": {
        "title": "Avengers Endgame: Encore",
        "release_date_india": "2026-09-25",
        "imdb_id": None,            # same IMDb page as the 2019 film
        "wikidata_id": None,
        "tmdb_id": None,
        "release_type": "re-release",
    },
    "AVG_DOOMSDAY_2026": {
        "title": "Avengers: Doomsday",
        "release_date_india": "2026-12-17",
        "imdb_id": "tt21357150",
        "wikidata_id": "Q113244839",
        "tmdb_id": "1003596",
        "release_type": "original",
    },
}

# Trailer launch dates we use as "day 0" for the 14-day attention window
TRAILER_DAY0 = {
    "AVG_ENDGAME_2019": "2018-12-07",   # first trailer (hA6hldpSTF8)
    "AVG_DOOMSDAY_2026": "2026-07-20",  # first full trailer (irVNGjRFZGk)
}

# ---- inflation ---------------------------------------------------------------
# Month we express all rupees in. Oct-2026 is the latest CPI print (released 12 Nov 2026).
CPI_TARGET_MONTH = "Oct-2026"
