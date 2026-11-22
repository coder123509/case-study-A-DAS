# Data inventory

Every field we actually use, after cleaning (`data/processed/`). Shape: S = structured, SS = semi-structured, U = unstructured.
Type: N = nominal, O = ordinal, D = discrete, C = continuous.

| Table | Field | Example | Shape of source | Type | Notes |
|---|---|---|---|---|---|
| films | film_id | 1 | - | N | our surrogate key |
| films | film_key | AVG_ENDGAME_2019 | - | N | the cleaned join key every source is matched to |
| films | title | Avengers: Endgame | SS (Wikidata JSON) | N | |
| films | release_date_india | 2019-04-26 | SS / trade | C (interval, date) | |
| films | release_type | original / re-release | - | N | |
| films | genres | action film\|adventure film\|superhero film | SS | N (multi-valued) | |
| films | runtime_min | 181 | SS | C (ratio) | NULL for unreleased Doomsday |
| films | imdb_id, wikidata_id, tmdb_id | tt4154796 | SS | N | identifiers used for matching |
| daily_collections | collection_date | 2019-04-26 | S (HTML table) | C (interval) | |
| daily_collections | day_no | 1 … 41 | S | D (and O: day order) | |
| daily_collections | weekday | Friday | S | N (cyclical) | |
| daily_collections | is_weekend, is_approx | 0/1 | S | N (binary) | |
| daily_collections | week_no | 1 … 6 | S | O | trade weeks run Fri-Thu |
| daily_collections | net_cr, net_cr_sacnilk, net_cr_bh | 53.6 | S | C (ratio, ₹ crore) | parsed from "₹ 53.60 Cr" |
| daily_collections | net_cr_english / hindi / tamil / telugu | 29.6 | S | C | Sacnilk language split |
| daily_collections | gross_cr_est | 64.45 | derived | C | net × 1.2025 |
| daily_collections | net_cr_real | 79.32 | derived | C | Oct-2026 rupees |
| daily_collections | net_source | sacnilk | - | N | lineage of each number |
| cpi_monthly | month | 2019-04-01 | S (MoSPI) | C (interval) | |
| cpi_monthly | cpi_base2012, cpi_base2024, cpi_linked_2024 | 141.2 / 74.37 | S | C (interval-type index) | |
| wiki_pageviews | view_date | 2018-12-07 | SS (JSON API) | C | |
| wiki_pageviews | views | 165032 | SS | D (count) | |
| youtube_videos | video_id | hA6hldpSTF8 | SS | N | |
| youtube_videos | channel, language | IndiaMarvel / Hindi | SS | N | |
| youtube_videos | published_at, snapshot_taken_at | 2018-12-07 13:01:21 | SS | C | |
| youtube_videos | duration_sec | 145 | SS | C (ratio) | |
| youtube_videos | view_count, like_count, comment_count | 112514610 | SS | D (count) | cumulative; came as text "3,377,553" |
| youtube_videos | days_online_at_snapshot | 2906 | derived | D | |
| reviews | text | "While I find it to be a bit too long…" | **U** | - (free text) | the unstructured field |
| reviews | source | rotten_tomatoes / imdb | - | N | |
| reviews | rating_10 | 9.0 | U-page metadata | O (0.5-star steps; we treat as ordinal) | |
| reviews | rating_label | positive / mixed / negative | derived | O | |
| reviews | review_date | 2026-10-05 | text → date | C | |
| reviews | verified, is_short, is_text_duplicate, theme_* | 0/1 | derived | N (binary) | |
| reviews | lang | en / es | derived | N | |
| reviews | n_words | 34 | derived | D | |
| reviews | vader_compound, model_pos_prob | 0.87 | derived | C | filled when VADER / IMDb-50K model are run |
| advance_booking | level | language / state / city | S | N | |
| advance_booking | area | Kerala | S | N | |
| advance_booking | gross_cr, gross_cr_wo_block | 0.994 | S | C | "₹99.40 Lac" → 0.994 Cr |
| advance_booking | tickets, shows | 25840 / 118 | S | D | "2.97 Lac" → 297000 |
| advance_booking | occupancy_pct | 72 | S | C (ratio, %) | |
| advance_booking | atp_rs, atp_rs_derived | 699 | S | C | average ticket price |
| release_schedule | first_show_note, show_screen_note | "2:30am and 3:00am shows" | U (article text) | - | |
| imdb_50k (Spark only) | review | text | U | - | 50,000 rows |
| imdb_50k (Spark only) | sentiment | positive / negative | labelled | N (binary) | |
