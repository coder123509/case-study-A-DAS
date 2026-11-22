"""
Step 3 - unstructured text: audience reviews / comments -> one tidy reviews table.

Inputs  : data/raw/reviews_rt/rt_endgame_audience_reviews_2026-11-21.tsv   (Rotten Tomatoes audience reviews, public page)
          data/raw/reviews_imdb/imdb_endgame_public_reviews.json            (the 5 reviews IMDb shows without login)
          data/raw/youtube_comments/*.csv   (OPTIONAL - only exists after running src/collect/youtube_api_collector.py)
Output  : data/interim/reviews_clean.csv
"""
import csv
import json
import re

import pandas as pd

from config import RAW, INTERIM, ACCESS_DATE
from utils import CleaningLog, clean_text

log = CleaningLog("s03_clean_reviews")
access = pd.Timestamp(ACCESS_DATE)

# ------------------------------------------------------------------ Rotten Tomatoes
rt = pd.read_csv(RAW / "reviews_rt" / "rt_endgame_audience_reviews_2026-11-21.tsv", sep="\t",
                 quoting=csv.QUOTE_NONE, dtype=str)
rt["source"] = "rotten_tomatoes"
rt["rating_raw"] = pd.to_numeric(rt["star_score"])          # 0.5 .. 5 stars
rt["rating_10"] = rt["rating_raw"] * 2                       # same 1-10 scale as IMDb


def relative_to_date(s):
    """'6 days ago' -> access_date - 6 days, 'Nov 14, 2026' -> that date"""
    s = str(s).strip()
    m = re.match(r"(\d+)\s+(day|hour|minute)s?\s+ago", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        return (access - pd.Timedelta(days=n)) if unit == "day" else access
    return pd.to_datetime(s, format="%b %d, %Y", errors="coerce")


rt["review_date"] = rt["timestamp_text"].map(relative_to_date)
n_rel = rt["timestamp_text"].str.contains("ago").sum()
log.add("rt_reviews", "relative dates like '6 days ago'", int(n_rel),
        f"converted using the access date {ACCESS_DATE}", "text dates -> datetime; error of +-1 day accepted")
rt["verified"] = rt["verified_review"].map({"true": True, "false": False})
rt = rt.rename(columns={"review_text": "text_raw"})

# ------------------------------------------------------------------ IMDb
with open(RAW / "reviews_imdb" / "imdb_endgame_public_reviews.json", encoding="utf-8") as fh:
    imdb_js = json.load(fh)
imdb = pd.json_normalize(imdb_js["reviews"])
imdb = imdb.rename(columns={"reviewId": "review_id", "reviewText": "text_raw", "authorRating": "rating_raw"})
imdb["source"] = "imdb"
imdb["rating_10"] = imdb["rating_raw"].astype(float)
imdb["review_date"] = pd.to_datetime(imdb["submissionDate"])
imdb["verified"] = pd.NA
imdb["text_raw"] = imdb["reviewSummary"] + ". " + imdb["text_raw"]
log.add("imdb_reviews", "IMDb hides all but 5 featured reviews unless you log in", 9718 - len(imdb),
        "used only the 5 public ones; did not log in", "assignment rule: never scrape behind a login")

parts = [rt, imdb]

# ------------------------------------------------------------------ YouTube comments (optional)
yt_files = sorted((RAW / "youtube_comments").glob("*.csv"))
if yt_files:
    ytc = pd.concat([pd.read_csv(f, dtype=str) for f in yt_files], ignore_index=True)
    ytc = ytc.rename(columns={"comment_id": "review_id", "text": "text_raw"})
    ytc["source"] = "youtube_comment"
    ytc["review_date"] = pd.to_datetime(ytc["published_at"], utc=True).dt.tz_localize(None)
    ytc["rating_10"] = pd.NA
    parts.append(ytc)
    print("youtube comment files:", len(yt_files), "rows:", len(ytc))
else:
    log.add("youtube_comments", "no comment files yet (needs a YouTube Data API key)", 0,
            "pipeline runs without them; collector script ready in src/collect/",
            "we only use official API for comments")

df = pd.concat(parts, ignore_index=True, sort=False)
df["film_key"] = df.get("film_key", pd.Series(index=df.index, dtype=object)).fillna("AVG_ENDGAME_2019")

# ------------------------------------------------------------------ text cleaning
df["text"] = df["text_raw"].map(clean_text)
n_html = df["text_raw"].astype(str).str.contains(r"&#39;|&quot;|<br", regex=True).sum()
log.add("all_reviews", "HTML entities and <br/> tags in text (&#39; &quot;)", int(n_html),
        "html.unescape + strip tags", "otherwise word counts and sentiment see junk tokens")

# drop exact empties
empty = df["text"].str.len() == 0
log.add("all_reviews", "empty text", int(empty.sum()), "dropped", "nothing to analyse")
df = df[~empty]

# duplicates: same id, or same text from same source (copy-paste bursts = possible fake buzz)
dup_id = df.duplicated(["source", "review_id"])
log.add("all_reviews", "duplicate review ids", int(dup_id.sum()), "dropped", "same record collected twice")
df = df[~dup_id]
df["text_norm"] = df["text"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True).str.strip()
dup_txt = df.duplicated(["source", "text_norm"], keep=False) & (df["text_norm"].str.split().str.len() > 3)
log.add("all_reviews", "identical long texts (copy-paste / bot check)", int(dup_txt.sum()),
        "kept but flagged is_text_duplicate", "short ones like 'masterpiece' repeat naturally; long identical texts would be suspicious")
df["is_text_duplicate"] = dup_txt

# very short reviews
df["n_words"] = df["text"].str.split().str.len()
df["n_chars"] = df["text"].str.len()
short = df["n_words"] < 3
log.add("all_reviews", "reviews under 3 words ('Masterpiece', 'Peak cinema')", int(short.sum()),
        "kept, flagged is_short", "they still carry a star rating; text models may ignore them")
df["is_short"] = short

# crude language check - our sentiment tools are English-only
EN_HINTS = {"the", "and", "is", "it", "was", "a", "to", "of", "movie", "film", "this", "i", "but", "great", "good", "love"}
ES_HINTS = {"lo", "que", "de", "la", "el", "y", "muy", "en", "película", "peor"}


def guess_lang(t):
    w = set(re.findall(r"[a-záéíóúñ]+", t.lower()))
    if len(w & ES_HINTS) >= 2 and len(w & ES_HINTS) > len(w & EN_HINTS):
        return "es"
    return "en"


df["lang"] = df["text"].map(guess_lang)
log.add("all_reviews", "non-English reviews (Spanish)", int((df["lang"] != "en").sum()),
        "kept, flagged lang='es', excluded from English sentiment", "VADER / our IMDb-trained model are English-only")

# star rating -> ordinal label we can use to TEST the sentiment model later
def star_label(r10):
    if pd.isna(r10):
        return pd.NA
    if r10 >= 7:
        return "positive"
    if r10 <= 4:
        return "negative"
    return "mixed"


df["rating_label"] = df["rating_10"].map(star_label)
log.add("all_reviews", "no sentiment label on our own reviews", len(df),
        "derived rating_label from stars (>=7/10 positive, <=4 negative, else mixed)",
        "lets us check the IMDb-50K model on OUR data, not only on its own test split")

# which release the review is about: the RT page is shared by the 2019 film and the 2026 Encore
df["viewing_context"] = "original_2019"
enc = (df["source"] == "rotten_tomatoes") & (df["review_date"] >= "2026-09-25")
df.loc[enc, "viewing_context"] = "encore_rerelease_2026"
log.add("all_reviews", "RT page is shared by the 2019 release and the Sep-2026 Encore re-release", int(enc.sum()),
        "viewing_context='encore_rerelease_2026' for reviews dated after 25-Sep-2026", "same film key, different moment in time")

# privacy: we never collected names/handles; make sure nothing slipped in
for col in ["author", "author_name", "username", "user_handle", "authorDisplayName", "author_channel_id"]:
    if col in df.columns:
        df = df.drop(columns=col)
        log.add("all_reviews", f"personal column '{col}' present", len(df), "dropped", "assignment privacy rule")

keep = ["source", "review_id", "film_key", "viewing_context", "review_date", "rating_raw", "rating_10", "rating_label",
        "verified", "lang", "n_words", "n_chars", "is_short", "is_text_duplicate", "text"]
df[keep].sort_values(["source", "review_date"]).to_csv(INTERIM / "reviews_clean.csv", index=False)
print("reviews_clean:", df.shape, df["source"].value_counts().to_dict())
log.save()
