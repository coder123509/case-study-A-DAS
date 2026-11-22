# Release Day Radar - Avengers: Endgame (2019) → Avengers: Doomsday (2026)

**Data and Storytelling · Module 1 · Case Study A**
Team: _TeamName_ · GitHub: `(https://github.com/coder123509/case-study-A-DAS.git)` _(add link)_

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
git clone https://github.com/<org-or-user>/release-day-radar.git
cd release-day-radar
python -m venv .venv
# Windows:  .venv\Scripts\activate      mac/linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Then , we copy the Homework 1.2 file to `data/raw/imdb_50k_corpus/IMDB Dataset.csv` (columns `review,sentiment`). It is not in git because it is 63 MB and not our data - see `data/raw/imdb_50k_corpus/README.md` for where it comes from.

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

- [ ] Put the IMDb 50K csv in place, `pip install vaderSentiment pyspark`, re-run `python run_pipeline.py` and `python spark/pyspark_text_job.py` (fills the sentiment columns and `outputs/spark/`).
- [ ] Load into MySQL and screenshot the query results for the report.
- [ ] After 17-Dec-2026: add Doomsday day-wise collections (same Sacnilk/BH format) and fill the "to be measured" rows of the Radar.
- [ ] Report (10 pages), slides (10), AI disclosure, contribution split.
