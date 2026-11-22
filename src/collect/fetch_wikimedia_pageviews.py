"""
Re-download the daily Wikipedia pageviews (Wikimedia REST API, JSON, no key needed).

    python src/collect/fetch_wikimedia_pageviews.py

Writes the same files that are already in data/raw/wikimedia_pageviews/.
API docs: https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/
Wikimedia asks for a descriptive User-Agent - please put your own email in it.
"""
import json
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parents[2] / "data" / "raw" / "wikimedia_pageviews"
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "ReleaseDayRadar student project (your-email@example.com)"}
BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{article}/daily/{start}/{end}"

JOBS = [
    ("Avengers:_Endgame", "20181201", "20190531", "endgame_20181201_20190531.json"),
    ("Avengers:_Doomsday", "20251201", "20261120", "doomsday_20251201_20261120.json"),
]

for article, start, end, fname in JOBS:
    url = BASE.format(article=requests.utils.quote(article, safe=""), start=start, end=end)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    js = r.json()
    with open(OUT / fname, "w", encoding="utf-8") as fh:
        json.dump(js, fh)
    print(fname, len(js["items"]), "days")
