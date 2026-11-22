"""
PySpark text job (Module 1 'Big data tools').

What it does, over ALL review/comment text we have (>= 50,000 rows thanks to the IMDb 50K corpus):
  1. clean   : lower-case, strip HTML (<br />), keep letters only
  2. measure : characters + words per review
  3. count   : term frequencies after removing stop words (overall and per group)
  4. aggregate by film / source: rows, avg length, share of reviews per theme keyword

Inputs
  data/raw/imdb_50k_corpus/IMDB Dataset.csv       (Homework 1.2 corpus, 50,000 rows, columns review,sentiment)
  data/interim/reviews_clean.csv                  (our RT + IMDb reviews, from src/s03_clean_reviews.py)
  data/raw/youtube_comments/*.csv                 (optional, from the API collector)

Outputs (folder outputs/spark/)
  row_counts.csv, length_by_group.csv, top_terms_by_group.csv, theme_share_by_group.csv, run_info.txt

Run (from project root):
    spark-submit spark/pyspark_text_job.py
or  python spark/pyspark_text_job.py          (pip install pyspark, needs Java 8/11/17)
"""
import os
import sys
import time
from pathlib import Path

from pyspark.sql import SparkSession, functions as F
from pyspark.ml.feature import StopWordsRemover

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "spark"
OUT.mkdir(parents=True, exist_ok=True)

spark = (SparkSession.builder
         .appName("release-day-radar-text")
         .master("local[*]")
         .config("spark.sql.shuffle.partitions", "8")      # small machine, small shuffle
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")
t0 = time.time()

# ------------------------------------------------------------------ load + union
corpus_path = ROOT / "data" / "raw" / "imdb_50k_corpus" / "IMDB Dataset.csv"
if not corpus_path.exists():
    sys.exit(f"Missing {corpus_path} - copy the Homework 1.2 IMDb 50K csv there (see README).")

# multiLine + escape because reviews contain commas, quotes and line breaks
imdb = (spark.read.option("header", True).option("multiLine", True).option("escape", '"')
        .csv(str(corpus_path))
        .select(F.col("review").alias("text"),
                F.lit("imdb_50k_corpus").alias("source"),
                F.lit("NO_FILM (practice corpus)").alias("film_key"),
                F.col("sentiment").alias("label")))

ours = (spark.read.option("header", True).option("multiLine", True).option("escape", '"')
        .csv(str(ROOT / "data" / "interim" / "reviews_clean.csv"))
        .select("text", "source", "film_key", F.col("rating_label").alias("label")))

frames = [imdb, ours]
yt_dir = ROOT / "data" / "raw" / "youtube_comments"
if any(yt_dir.glob("*.csv")):
    yt = (spark.read.option("header", True).option("multiLine", True).option("escape", '"')
          .csv(str(yt_dir / "*.csv"))
          .select("text", F.lit("youtube_comment").alias("source"), "film_key", F.lit(None).cast("string").alias("label")))
    frames.append(yt)

df = frames[0]
for f in frames[1:]:
    df = df.unionByName(f)
rows_read = df.count()                            # before empty-text drops and de-duplication

# ------------------------------------------------------------------ 1. clean
df = (df.filter(F.col("text").isNotNull())
        .withColumn("clean", F.lower(F.col("text")))
        .withColumn("clean", F.regexp_replace("clean", r"<br\s*/?>", " "))
        .withColumn("clean", F.regexp_replace("clean", r"&#39;|&quot;|&amp;", " "))
        .withColumn("clean", F.regexp_replace("clean", r"[^a-z\s]", " "))
        .withColumn("clean", F.trim(F.regexp_replace("clean", r"\s+", " ")))
        .filter(F.length("clean") > 0))
df = df.dropDuplicates(["source", "clean"])          # exact duplicate texts (the IMDb corpus has a few hundred)
df.cache()

# ------------------------------------------------------------------ 2. measure
df = (df.withColumn("words", F.split("clean", " "))
        .withColumn("n_words", F.size("words"))
        .withColumn("n_chars", F.length("text")))

row_counts = df.groupBy("source", "film_key").count().orderBy(F.desc("count"))
row_counts.toPandas().to_csv(OUT / "row_counts.csv", index=False)
total_rows = df.count()

length_by_group = (df.groupBy("source", "film_key", "label")
                     .agg(F.count("*").alias("n"),
                          F.round(F.avg("n_words"), 1).alias("avg_words"),
                          F.expr("percentile_approx(n_words, 0.5)").alias("median_words"),
                          F.round(F.avg("n_chars"), 1).alias("avg_chars"))
                     .orderBy("source", "film_key", "label"))
length_by_group.toPandas().to_csv(OUT / "length_by_group.csv", index=False)

# ------------------------------------------------------------------ 3. count terms
extra_stop = ["movie", "film", "one", "like", "just", "really", "even", "also", "would", "much", "get", "see", "s", "t",
              "br", "will", "can", "time", "make", "made", "watch", "watching", "think", "know", "seen", "say"]
remover = StopWordsRemover(inputCol="words", outputCol="tokens",
                           stopWords=StopWordsRemover.loadDefaultStopWords("english") + extra_stop)
tok = remover.transform(df).select("source", "film_key", F.explode("tokens").alias("term")).filter(F.length("term") > 2)

term_counts = tok.groupBy("source", "film_key", "term").count()
from pyspark.sql.window import Window
w = Window.partitionBy("source", "film_key").orderBy(F.desc("count"))
top_terms = term_counts.withColumn("rank", F.row_number().over(w)).filter(F.col("rank") <= 25).orderBy("source", "film_key", "rank")
top_terms.toPandas().to_csv(OUT / "top_terms_by_group.csv", index=False)

# ------------------------------------------------------------------ 4. aggregate themes by film (same dictionary idea as s05)
THEMES = {
    "story_plot": r"\b(story|plot|script|writing)\b",
    "length_pacing": r"\b(long|length|runtime|pacing|slow|boring)\b",
    "emotion": r"\b(cry|cried|tears|emotional|goosebumps)\b",
    "action_vfx": r"\b(action|fight|battle|visual|visuals|effects|cgi)\b",
    "acting": r"\b(acting|actor|actors|actress|performance|cast)\b",
    "music": r"\b(music|score|soundtrack|song|songs)\b",
    "price_value": r"\b(price|money|ticket|worth|waste)\b",
}
agg = [F.count("*").alias("n")]
for name, pat in THEMES.items():
    agg.append(F.round(100 * F.avg(F.col("clean").rlike(pat).cast("int")), 2).alias(f"pct_{name}"))
theme_share = df.groupBy("source", "film_key").agg(*agg).orderBy("source", "film_key")
theme_share.toPandas().to_csv(OUT / "theme_share_by_group.csv", index=False)

elapsed = time.time() - t0
info = (f"rows read: {rows_read}\n"
        f"rows removed while cleaning: {rows_read - total_rows}\n"
        f"rows after cleaning and de-duplication: {total_rows}\n"
        f"spark version: {spark.version}\n"
        f"partitions: {df.rdd.getNumPartitions()}\n"
        f"runtime seconds: {elapsed:.1f}\n")
(OUT / "run_info.txt").write_text(info)
print(info)
row_counts.show(truncate=False)
theme_share.show(truncate=False)
spark.stop()
