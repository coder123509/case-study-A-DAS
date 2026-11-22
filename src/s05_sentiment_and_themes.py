"""
Step 5 - sentiment + "what are people talking about" (themes).

Plan (same as in our proposal):
  1. Build/test the sentiment method on the LABELLED IMDb 50K corpus (Homework 1.2):
       a) VADER (rule based, no training)            -> accuracy on the 50K labels
       b) TF-IDF + Logistic Regression (trained)     -> accuracy on a held-out 20%
  2. Apply the better one to OUR unlabelled reviews.
  3. Check it again on our reviews using the star rating as a rough label (rating_label from step 3).
  4. Themes: simple keyword dictionary (story, length, emotion, action/VFX, extra scenes, price, format, Doomsday hype).

What you need on your machine:
  - data/raw/imdb_50k_corpus/IMDB Dataset.csv   (columns: review, sentiment)  -> see README
  - pip install vaderSentiment
If either is missing the script still runs and simply skips that part (it tells you).

Outputs: data/interim/reviews_scored.csv, outputs/tables/sentiment_model_eval.csv,
         outputs/tables/theme_summary.csv
"""
import re

import numpy as np
import pandas as pd

from config import RAW, INTERIM, TABLES
from utils import CleaningLog, clean_text

log = CleaningLog("s05_sentiment")
reviews = pd.read_csv(INTERIM / "reviews_clean.csv", parse_dates=["review_date"])
eval_rows = []

# ------------------------------------------------------------------ VADER
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader = SentimentIntensityAnalyzer()
except ImportError:
    vader = None
    print("! vaderSentiment not installed -> pip install vaderSentiment (VADER part skipped)")


def vader_label(compound):
    # standard VADER cut-offs
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "mixed"


# ------------------------------------------------------------------ IMDb 50K corpus
corpus_path = RAW / "imdb_50k_corpus" / "IMDB Dataset.csv"
model = None
if corpus_path.exists():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.metrics import accuracy_score, f1_score

    imdb = pd.read_csv(corpus_path)
    before = len(imdb)
    imdb = imdb.drop_duplicates("review")
    log.add("imdb_50k", "duplicate reviews in the 50K corpus", before - len(imdb), "dropped", "duplicates would leak between train and test")
    imdb["review"] = imdb["review"].map(clean_text)          # same <br /> problem as our data
    y = (imdb["sentiment"] == "positive").astype(int)

    X_tr, X_te, y_tr, y_te = train_test_split(imdb["review"], y, test_size=0.2, random_state=42, stratify=y)
    model = make_pipeline(TfidfVectorizer(min_df=3, ngram_range=(1, 2), max_features=100_000, sublinear_tf=True),
                          LogisticRegression(max_iter=1000))
    model.fit(X_tr, y_tr)
    pred = model.predict(X_te)
    eval_rows.append({"method": "TF-IDF + LogReg", "test_set": "IMDb 50K held-out 20%", "n": len(y_te),
                      "accuracy": round(accuracy_score(y_te, pred), 4), "f1": round(f1_score(y_te, pred), 4)})

    if vader is not None:
        sample = X_te.sample(5000, random_state=1)            # VADER is slow-ish, 5k is plenty
        vp = sample.map(lambda t: int(vader.polarity_scores(t)["compound"] >= 0.05))
        eval_rows.append({"method": "VADER", "test_set": "IMDb 50K held-out (5k sample)", "n": len(sample),
                          "accuracy": round(accuracy_score(y_te.loc[sample.index], vp), 4),
                          "f1": round(f1_score(y_te.loc[sample.index], vp), 4)})
else:
    print(f"! {corpus_path} not found -> model training skipped (see README, 'IMDb 50K corpus')")

# ------------------------------------------------------------------ score our reviews
en = reviews["lang"] == "en"
reviews["vader_compound"] = np.nan
reviews["vader_label"] = pd.NA
reviews["model_pos_prob"] = np.nan
reviews["model_label"] = pd.NA

if vader is not None:
    reviews.loc[en, "vader_compound"] = reviews.loc[en, "text"].map(lambda t: vader.polarity_scores(t)["compound"])
    reviews.loc[en, "vader_label"] = reviews.loc[en, "vader_compound"].map(vader_label)

if model is not None:
    p = model.predict_proba(reviews.loc[en, "text"])[:, 1]
    reviews.loc[en, "model_pos_prob"] = p
    reviews.loc[en, "model_label"] = np.where(p >= 0.6, "positive", np.where(p <= 0.4, "negative", "mixed"))

# how well do they agree with the stars on OUR data? (positive vs negative only, mixed dropped)
check = reviews[en & reviews["rating_label"].isin(["positive", "negative"])]
for col, name in [("vader_label", "VADER"), ("model_label", "TF-IDF + LogReg")]:
    sub = check[check[col].isin(["positive", "negative"])]
    if len(sub):
        eval_rows.append({"method": name, "test_set": "our reviews, stars as label", "n": len(sub),
                          "accuracy": round((sub[col] == sub["rating_label"]).mean(), 4), "f1": np.nan})

pd.DataFrame(eval_rows).to_csv(TABLES / "sentiment_model_eval.csv", index=False)
if eval_rows:
    print(pd.DataFrame(eval_rows).to_string())

# ------------------------------------------------------------------ themes
THEMES = {
    "story_plot": r"\b(?:story|plot|storyline|writing|script|time ?travel|heist|plot holes?)\b",
    "length_pacing": r"\b(?:long|length|run ?time|3 ?h(?:ours?)?|three hours?|pacing|slow|dragged|too long)\b",
    "emotion": r"\b(?:cry|cried|tears|emotional|goosebumps|feels|heart ?break\w*|heartbreaking|nostalgi\w*)\b",
    "action_vfx": r"\b(?:action|fight|battle|visuals?|effects|vfx|spectacle|cgi)\b",
    "characters_acting": r"\b(?:acting|actors?|cast|characters?|performance|iron man|tony|captain|thor|hulk|thanos)\b",
    "extra_scenes_encore": r"\b(?:encore|extra scenes?|new scenes?|added|credits? scenes?|post[- ]credits?|bonus)\b",
    "price_value": r"\b(?:price|money|cash ?grab|ticket|\$\d+|worth|ripoff|rip-off|charge)\b",
    "format_experience": r"\b(?:imax|infinity vision|4dx|dolby|screen ?x|big screen|theat(?:er|re)s?)\b",
    "doomsday_hype": r"\b(?:doomsday|doom|secret wars|next (?:one|movie)|can'?t wait)\b",
}
for name, pat in THEMES.items():
    reviews[f"theme_{name}"] = reviews["text"].str.contains(pat, flags=re.I, regex=True)

rows = []
for name in THEMES:
    m = reviews[f"theme_{name}"]
    rows.append({
        "theme": name,
        "n_reviews": int(m.sum()),
        "share_of_reviews_pct": round(100 * m.mean(), 1),
        "avg_rating_10_with_theme": round(reviews.loc[m, "rating_10"].mean(), 2),
        "avg_rating_10_without": round(reviews.loc[~m, "rating_10"].mean(), 2),
        "share_negative_with_theme_pct": round(100 * (reviews.loc[m, "rating_label"] == "negative").mean(), 1),
    })
themes = pd.DataFrame(rows).sort_values("n_reviews", ascending=False)
themes["rating_gap"] = (themes["avg_rating_10_with_theme"] - themes["avg_rating_10_without"]).round(2)
themes.to_csv(TABLES / "theme_summary.csv", index=False)
print(themes.to_string())
log.add("themes", "theme keywords are our own dictionary (no labelled theme data)", len(reviews),
        "regex dictionary, kept in this file so anyone can audit / change it", "transparent > clever for a 145-review sample")

reviews.to_csv(INTERIM / "reviews_scored.csv", index=False)
log.save()
