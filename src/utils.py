"""
Small helpers shared by the cleaning scripts:
  - money / count parsers  ("₹ 53.60 Cr", "2.97 Lac", "1,25,00,000")
  - film-name matching
  - CleaningLog: every script appends rows here -> outputs/tables/cleaning_log.csv
"""
import re
import html
import difflib
import pandas as pd

from config import FILMS, TABLES

# ---------------------------------------------------------------------------
# Money and counts
# ---------------------------------------------------------------------------
CRORE = 1e7
LAKH = 1e5


def parse_inr_to_crore(text):
    """
    Turn the different ways Indian trade sites write money into a float in crore.

    '₹ 53.60 Cr [En: 29.60; ...]' -> 53.6
    '₹53.6 cr.'                   -> 53.6
    '₹37.32 Lac'                  -> 0.3732
    '1,25,00,000'                 -> 1.25   (plain rupees, Indian digit grouping)
    '₹20.77 Cr [₹18.40 Cr]'       -> 20.77  (first number = incl. block seats)
    Returns None if nothing usable is there (we log those, we don't guess).
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = str(text).strip()
    if s in ("", "-", "–", "N/A"):
        return None
    # only look at the part before any bracket (language split / without-block value)
    s = s.split("[")[0]
    s = s.replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()

    m = re.search(r"([\d,]*\.?\d+)\s*(cr|crore|lac|lakh|lakhs)?", s, flags=re.I)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit.startswith("cr"):
        return num
    if unit.startswith("la"):
        return num * LAKH / CRORE
    # no unit -> assume plain rupees
    return num / CRORE


def parse_indian_count(text):
    """'2.97 Lac' -> 297000, '47,514' -> 47514, '1.07 Lac' -> 107000"""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = str(text).split("[")[0].strip()
    m = re.search(r"([\d,]*\.?\d+)\s*(lac|lakh|k)?", s, flags=re.I)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit in ("lac", "lakh"):
        num *= LAKH
    elif unit == "k":
        num *= 1000
    return int(round(num))


def parse_pct(text):
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    m = re.search(r"(-?[\d.]+)\s*%", str(text))
    return float(m.group(1)) if m else None


def clean_text(text):
    """HTML entities + <br/> tags out, whitespace squashed."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    t = html.unescape(str(text))
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Film-name matching
# ---------------------------------------------------------------------------
def _norm_title(t):
    t = clean_text(t).lower()
    t = t.replace("’", "'").replace("–", "-")
    # trailer / marketing junk that YouTube adds to titles
    junk = [
        r"marvel studios'?", r"official( hindi)? trailer", r"official teaser trailer",
        r"special look", r"in (theaters|theatres|cinemas) .*", r"\| hindi",
        r"only in theaters.*", r"\(\d{4}\)", r"will return",
    ]
    for j in junk:
        t = re.sub(j, " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# hand-written rules first (exact, explainable), fuzzy match only as a fallback
_RULES = [
    (r"encore", "AVG_ENCORE_2026"),
    (r"doomsday", "AVG_DOOMSDAY_2026"),
    (r"q113244839", "AVG_DOOMSDAY_2026"),      # Wikidata label was missing -> came back as the QID
    (r"end ?game", "AVG_ENDGAME_2019"),
    (r"avengers 4", "AVG_ENDGAME_2019"),
    (r"q23781155", "AVG_ENDGAME_2019"),
]


def match_film(raw_title, published_year=None):
    """
    Map any raw title to our film key. Returns (film_key, method).
    published_year is used for the one tricky case: Endgame's Dec-2018 trailers are
    titled just 'Avengers - Official Trailer' (the name 'Endgame' was revealed IN the trailer).
    """
    n = _norm_title(raw_title)
    for pattern, key in _RULES:
        if re.search(pattern, n):
            return key, f"rule:{pattern}"

    if n in ("avengers", "avengers official trailer") and published_year in (2018, 2019):
        return "AVG_ENDGAME_2019", "rule:untitled-avengers-trailer-2018"

    # fuzzy fallback against the clean titles
    choices = {_norm_title(v["title"]): k for k, v in FILMS.items()}
    best = difflib.get_close_matches(n, list(choices), n=1, cutoff=0.75)
    if best:
        return choices[best[0]], f"fuzzy:{best[0]}"
    return None, "unmatched"


# ---------------------------------------------------------------------------
# Cleaning log
# ---------------------------------------------------------------------------
class CleaningLog:
    """Collects one row per cleaning decision. Each script saves its own part,
    run_pipeline.py stitches them into outputs/tables/cleaning_log.csv"""

    def __init__(self, step):
        self.step = step
        self.rows = []

    def add(self, dataset, problem, rows_affected, action, reason):
        self.rows.append({
            "step": self.step,
            "dataset": dataset,
            "problem": problem,
            "rows_affected": int(rows_affected),
            "action": action,
            "reason": reason,
        })
        print(f"  [log] {dataset}: {problem} -> {action} ({rows_affected} rows)")

    def save(self):
        out = TABLES / f"cleaning_log_{self.step}.csv"
        pd.DataFrame(self.rows).to_csv(out, index=False)
        return out
