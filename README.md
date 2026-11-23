# Release Day Radar - Avengers: Endgame (2019) → Avengers: Doomsday (2026)

**Data and Storytelling · Module 1 · Case Study A**
Team Members:1)Abhinav Krishna Rayachoti 2)Aayushh K P Naik 3)Abhishek Varma · GitHub: [case-study-A-DAS](https://github.com/coder123509/case-study-A-DAS.git)

We are the data desk of a film distributor. The Head of Distribution has to decide, within 72 hours of a release, whether to add screens, cut screens or spend more on promotion. We asked:

> **To what extent can online attention, engagement and audience sentiment around *Avengers: Endgame* and *Avengers: Doomsday* help anticipate theatrical demand in India - and how should release timing, show availability and inflation be handled when turning that into a screen-allocation and promotion framework?**

Endgame (India release 26-Apr-2019) is our historical reference, tracked day by day from its first trailer (7-Dec-2018). Doomsday (India release **17-Dec-2026**, a Thursday) is the upcoming film we apply it to. Along the way we found a useful third data point: **Avengers Endgame: Encore**, the same film re-released in India on 25-Sep-2026 - the same title, sold in 2026 prices to a fan-only audience.

---

## 1. What is in this repo

```
release-day-radar/
├── README.md                 <- you are here
├── requirements.txt
├── run_pipeline.py           <- runs every step from raw data to charts
├── data/
│   ├── raw/                  <- exactly what we collected (never edited by code)
│   │   ├── wikimedia_pageviews/   JSON  (Wikimedia REST API)       semi-structured
│   │   ├── wikidata/              JSON  (Wikidata SPARQL)          semi-structured
│   │   ├── youtube/               JSON  (trailer stats snapshot)   semi-structured
│   │   ├── box_office/            HTML / text tables (Sacnilk, Bollywood Hungama)   structured
│   │   ├── cpi/                   official MoSPI CPI values + linking factors       structured
│   │   ├── manual_compiled/       small CSVs of figures quoted in trade/press articles (URL per row)
│   │   ├── reviews_rt/            Rotten Tomatoes audience reviews (TSV)           unstructured
│   │   ├── reviews_imdb/          the 5 public IMDb reviews (JSON)                 unstructured
│   │   ├── youtube_comments/      empty until you run the YouTube API collector
│   │   └── imdb_50k_corpus/       put the Homework 1.2 IMDb 50K csv here (not in git)
│   ├── interim/              <- cleaned, one file per source (made by src/s01-s05)
│   └── processed/            <- final tables = one CSV per MySQL table (made by src/s06)
├── src/
│   ├── config.py             paths, film keys, trailer dates
│   ├── utils.py              money/count parsers, film-name matching, CleaningLog
│   ├── s01_flatten_json.py   json_normalize the 3 JSON sources
│   ├── s02_clean_box_office.py   parse + reconcile Sacnilk vs Bollywood Hungama, advance booking
│   ├── s03_clean_reviews.py  text cleaning, dates, duplicates, language, privacy
│   ├── s04_inflation_adjust.py   CPI base-2012 → base-2024 linking, real rupees
│   ├── s05_sentiment_and_themes.py  VADER + TF-IDF/LogReg (trained on IMDb 50K) + theme keywords
│   ├── s06_build_tables.py   relational tables for MySQL
│   ├── s07_analysis_charts.py    numbers + 7 charts (titles = findings)
│   ├── s08_radar_framework.py    decision checklist + opening-day scenarios
│   └── collect/              scripts to re-download the API data (Wikimedia, Wikidata, YouTube API)
├── sql/
│   ├── schema.sql            8 tables, primary/foreign keys
│   ├── load_data.sql         loads data/processed/*.csv
│   ├── queries.sql           9 queries (JOINs, GROUP BY, HAVING, subquery, window function)
│   └── check_queries_sqlite.py   smoke test of the queries without a MySQL server
├── spark/pyspark_text_job.py PySpark job over ≥ 50,000 review rows
├── spreadsheet/              one cleaning step done in Excel + the same step in pandas
├── outputs/
│   ├── charts/               c1 … c7 PNGs, plus charts/sql/ for Q1, Q3 and Q9
│   └── tables/               cleaning_log.csv, key_numbers.csv, radar_checklist.csv, …
│       └── sql/              full result of each query, plus query_results.txt
└── docs/                     source register, data inventory, V profile, ER diagram,
                              cleaning log, spreadsheet-vs-pandas note, findings notes,
                              AI disclosure + team contribution templates
```

## 2. Setup (once)

You need **Python 3.10+**. For SQL: **MySQL 8**. For Spark: **Java 8, 11 or 17** (check with `java -version`).

```bash
git clone https://github.com/coder123509/case-study-A-DAS.git
cd case-study-A-DAS
python -m venv .venv
# Windows:  .venv\Scripts\activate      mac/linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Then , we copy the Homework 1.2 file to `data/raw/imdb_50k_corpus/IMDB Dataset.csv` (columns `review,sentiment`). (It is not in git because it is 63 MB and not our data - see `data/raw/imdb_50k_corpus/README.md` for where it comes from.)

Link to the dataset: https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews

## 3. How to run everything (in this order)

| Step | Command | What you get |
|---|---|---|
| 1. Pipeline (raw → charts) | `python run_pipeline.py` | `data/interim/`, `data/processed/`, `outputs/charts/`, `outputs/tables/`, `docs/cleaning_log.md` |
| 2. MySQL | `mysql -u root -p < sql/schema.sql` <br> `mysql --local-infile=1 -u root -p release_day_radar < sql/load_data.sql` <br> `mysql -u root -p release_day_radar < sql/queries.sql` | database `release_day_radar` with 8 tables, row counts printed at the end of the load |
| 2b. (no MySQL handy) | `python sql/check_queries_sqlite.py` | runs the same 9 queries on SQLite, writes every row to `outputs/tables/sql/`, and charts Q1, Q3 and Q9 (the ones c1–c7 do not already show) |
| 3. PySpark | `python spark/pyspark_text_job.py` (or `spark-submit spark/pyspark_text_job.py`) | `outputs/spark/` - row counts, length stats, top terms, theme shares, run time |
| 4. Spreadsheet vs pandas | open `spreadsheet/endgame_daywise_cleaning.xlsx`, then `python spreadsheet/compare_with_pandas.py` | proof both tools give the same 21 rows |
| 5. (optional) fresh API data | `python src/collect/fetch_wikimedia_pageviews.py` · `python src/collect/fetch_wikidata_metadata.py` · `python src/collect/youtube_api_collector.py --comments` (needs `YT_API_KEY`) | updated raw files; rerun step 1 |

Run every command from the **project root**. If `load_data.sql` complains about `local_infile`, run `SET GLOBAL local_infile = 1;` once as root.

**Sentiment note:** `s05` trains the TF-IDF + logistic regression model on the IMDb 50K corpus and runs VADER. If the corpus file or `vaderSentiment` is missing, the step prints a warning, still writes the theme analysis, and leaves the sentiment columns empty - so put the corpus in place before the final run. Results go to `outputs/tables/sentiment_model_eval.csv` (accuracy on the IMDb test split *and* on our own reviews, using their star ratings as labels).

## 4. Data we used (full details: `docs/source_register.md`)

| Shape | Source | Format | What it gives us |
|---|---|---|---|
| Semi-structured | **Wikimedia Pageviews REST API** | JSON API | daily English-Wikipedia views - Endgame 1-Dec-2018 → 31-May-2019, Doomsday 1-Dec-2025 → 20-Nov-2026 (our daily *attention* signal, covers the 14-day trailer window) |
| Semi-structured | **Wikidata SPARQL** | JSON API | IMDb/TMDb ids, genres, runtime, release dates |
| Semi-structured | **YouTube** (Marvel Entertainment, IndiaMarvel) | JSON | views/likes for 16 official trailers (English + Hindi), snapshot of 21-Nov-2026 |
| Structured | **Sacnilk**, **Bollywood Hungama** | HTML tables | day-wise India net for Endgame (2019) and Encore (2026), language split, weekly, territory, chain |
| Structured | **Sacnilk advance tracker** | text tables | Doomsday Day-1 advance by language, state, city (21-Nov-2026) |
| Structured | **MoSPI CPI** (official) | PDF tables → CSV | CPI Combined, base 2012 and base 2024 + the official linking factor 0.5267 |
| Unstructured | **Rotten Tomatoes** audience reviews, **IMDb** public reviews | free text | 145 reviews (text + stars) |
| Practice corpus | IMDb 50K (Homework 1.2) | labelled CSV | training/testing the sentiment method, PySpark volume |

Rules we followed: official APIs where they exist, no logins, no usernames or profile links stored, every number traceable to a URL, trade figures treated as estimates (we keep both sources when they disagree).

**Changes from our proposal:** Reddit could not be reached from our collection setup → replaced by Rotten Tomatoes audience reviews. TMDb/OMDb need keys → Wikidata gives the same metadata (and the TMDb id). YouTube comments → only via the official API (script ready).

## 5. Where each Module-1 requirement is

| Requirement | Evidence |
|---|---|
| Data types (N/O/D/C, S/SS/U) | `docs/data_inventory.md` |
| 3 Vs | `docs/v_profile.md` |
| 3+ sources, 1+ JSON API, all three shapes | `docs/source_register.md` (10 sources incl. 2 JSON APIs, + the practice corpus) |
| `json_normalize` | `src/s01_flatten_json.py` |
| MySQL, ≥3 related tables, ER diagram, 5+ queries with JOIN + GROUP BY | `sql/schema.sql`, `docs/er_diagram.md`, `sql/queries.sql` (9 queries) |
| Spreadsheet vs pandas | `spreadsheet/`, `docs/spreadsheet_vs_pandas.md` |
| Missing values, type casting, film-name matching | `docs/cleaning_log.md` (45 logged decisions), `src/utils.py` |
| Normalisation | chart c1 (launch day = 100 index + min-max column in `outputs/tables/trailer_window_14d.csv`), c2 (z-scores), c5 (% of day 1); inflation separately in c3 |
| PySpark ≥ 50,000 rows | `spark/pyspark_text_job.py` → `outputs/spark/` |
| Reproducible pipeline | `run_pipeline.py` + this README |
| ≥3 charts titled with findings, ≥1 combining sources | `outputs/charts/` (c2 = Wikimedia + box office; c3 = box office + CPI; c4 = press + CPI + Sacnilk) |

## 6. Main outputs at a glance

| Chart | Finding (title) |
|---|---|
| c1 trailer attention, 14 days | Doomsday's trailer buzz faded faster: day 3 kept 33 % of launch-day attention vs 50 % for Endgame |
| c2 buzz vs box office (Endgame) | Attention and ticket sales moved together (r = 0.97) - but both are driven by the release itself |
| c3 inflation | In today's money Endgame's India run is worth ~₹552 Cr, not ₹373 Cr (prices +48 % since Apr-2019) |
| c4 ticket price vs CPI | CPI explains ₹318 for a ₹215 ticket; Doomsday fans are paying ₹699 |
| c5 daily decay | Monday test: Endgame kept 58 % of its Friday, the re-release only 31 % |
| c6 review themes | Value-for-money complaints sink ratings: 5.9/10 vs 8.9 for everything else |
| c7 Doomsday advance by state | Kerala, Telangana, Tamil Nadu are already 60 %+ full, 26 days out |

The decision framework is `outputs/tables/radar_checklist.csv` (what to check, when, the benchmark, and the action) and `outputs/tables/doomsday_opening_scenarios.csv` (₹53.6 / 79.3 / 94.0 Cr opening-day net, with assumptions). Draft wording for the report is in `docs/findings_notes.md`.

## 7. Row counts (after `run_pipeline.py`)

| MySQL table | rows |
|---|---|
| films | 3 |
| daily_collections | 69 |
| wiki_pageviews | 537 |
| youtube_videos | 16 |
| reviews | 145 |
| advance_booking | 27 |
| cpi_monthly | 24 |
| release_schedule | 3 |

## 8. Known limitations (more in `docs/findings_notes.md`)

- One past film (+ one re-release) cannot support a predictive model; the Radar gives benchmarks and rules, not a forecast.
- English Wikipedia attention is global, not India-only; YouTube counters are cumulative snapshots.
- 145 reviews, all RT ones from the 2026 re-release period; online reviewers ≠ all moviegoers; IMDb hides most reviews behind login.
- Trade sources disagree (Endgame lifetime 370.05 / 373.05 / 373.22 Cr) - shown as ranges.
- CPI ≠ cinema ticket prices; Nov-2026 CPI not yet published (Oct-2026 used).
- Doomsday's week 2 has Christmas/New-Year holidays; Endgame's didn't.

## 9. Final results

### 9.1 What we answered
Online attention moves closely with ticket sales, but one past film and one re-release are not enough to forecast. So our result is a **Release Day Radar**: a checklist of what to watch, when, the benchmark to compare against, and the action to take (`outputs/tables/radar_checklist.csv`).

### 9.2 Main findings
1. **Attention and sales move together.** Endgame's daily Wikipedia views and daily India net collections correlate at r = 0.97 over days 1-28. It stays at r = 0.89 on days 8-28 only, so it is not just the opening-week spike. Both are driven by the release itself, so this is not proof of cause.
2. **Doomsday's trailer buzz faded faster.** On day 3 of the 14-day trailer window it kept 33% of its launch-day attention, against 50% for Endgame. Its window did have more total views (1.03M vs 0.85M).
3. **The Monday test separates a strong run from a weak one.** Endgame kept 58% of its Friday collection on Monday. The Encore re-release kept 31%. On the second Friday, Endgame held 22% of its first Friday and Encore 17%.
4. **Inflation changes the comparison.** Prices rose about 48% between April 2019 and October 2026 (CPI factor 1.4798). Endgame's India run is worth about Rs 552 Cr in today's money, not Rs 373 Cr. A Rs 215 ticket in 2019 equals about Rs 318 now, while Doomsday fans are paying Rs 699.
5. **Value for money hurts reviews most.** Reviews that mention value for money average 5.9/10, against 8.9 for all other reviews.
6. **Early Doomsday advance booking is uneven.** About 26 days before release, Kerala, Telangana and Tamil Nadu were already over 60% full.
7. **Opening-day scenarios for Doomsday** (assumptions are in `outputs/tables/doomsday_opening_scenarios.csv`): Rs 53.6 Cr, Rs 79.3 Cr and Rs 94.0 Cr net. These are planning scenarios, not predictions.

### 9.3 What the Radar tells the Head of Distribution
- **Before release:** track trailer-window attention against Endgame's fade curve, advance booking by state, and review themes.
- **Day 1-3:** compare daily net with the 58% (Endgame) and 31% (Encore) Monday benchmarks to decide whether to add or cut screens.
- **Week 2:** use the second-Friday benchmarks (22% / 17%), but treat Doomsday's week 2 carefully because it includes Christmas and New Year.
- **After 17-Dec-2026:** add Doomsday's real day-wise collections and fill the "to be measured" rows of the Radar.

### 9.4 Results from the technical work
| Item | Result |
|---|---|
| Data shapes covered | Structured, semi-structured (JSON APIs, flattened with `json_normalize`) and unstructured (reviews) |
| Sources | 10 public sources plus the IMDb 50K practice corpus; nothing fabricated |
| Cleaning log | 49 logged decisions (missing values, types, film-name matching, normalisation) |
| MySQL | 8 tables with primary and foreign keys; row counts in section 7 match the pipeline; query outputs in `images/` |
| PySpark | 50,145 rows read, 49,721 analysed after removing empty and duplicate texts, 424 dropped |
| Sentiment | VADER and TF-IDF + logistic regression compared; about 90% accuracy on IMDb 50K (exact figures in `outputs/tables/sentiment_model_eval.csv`) |
| Spreadsheet vs pandas | Same 21 rows from both tools |
| Charts | 7 charts with findings as titles; c2, c3 and c4 combine more than one source |

### 9.5 Limits
- One past film and one re-release cannot support a predictive model.
- English Wikipedia attention is global, not India-only.
- 145 reviews, all Rotten Tomatoes ones from the 2026 re-release period are not all moviegoers.
- Trade sources disagree (Endgame lifetime 370.05 / 373.05 / 373.22 Cr), so we show ranges.
- CPI is general inflation, not cinema ticket pricing. October 2026 CPI was used because November is not yet published.
- YouTube API v3 could not be used to scrape live youtube content due to constraints. Instead, we used alternatives like IMDb and Rotten Tomatoes reviews.
