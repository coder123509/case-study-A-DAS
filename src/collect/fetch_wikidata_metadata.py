"""
Re-run the Wikidata SPARQL query for film metadata (JSON, no key needed).

    python src/collect/fetch_wikidata_metadata.py

The query itself is stored in data/raw/wikidata/query.rq so it can be pasted into
https://query.wikidata.org as well.
"""
import json
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "wikidata"
query = (RAW / "query.rq").read_text(encoding="utf-8")

r = requests.get("https://query.wikidata.org/sparql",
                 params={"query": query, "format": "json"},
                 headers={"User-Agent": "ReleaseDayRadar student project (your-email@example.com)"},
                 timeout=60)
r.raise_for_status()
with open(RAW / "wikidata_film_metadata.json", "w", encoding="utf-8") as fh:
    json.dump(r.json(), fh, indent=2)
print("rows:", len(r.json()["results"]["bindings"]))
