# V profile (one page)

## Volume
| Data | Rows | Size on disk |
|---|---|---|
| Wikimedia pageviews (2 films, daily) | 537 | 91 KB (JSON) |
| Wikidata metadata | 2 | 2 KB |
| YouTube trailer snapshot | 16 videos | 10 KB |
| Box office (Sacnilk + Bollywood Hungama, day/week/territory/chain tables) | 69 daily rows + 8 weekly + 25 others | 10 KB |
| Doomsday advance booking snapshot | 27 rows | 3 KB |
| CPI (official) | 27 index values + 3 linking factors | 6 KB |
| Audience reviews (RT 140 + IMDb 5) | 145 reviews, ~4,900 words | 37 KB |
| **Our own collected data, total** | **~830 rows** | **~170 KB raw, 90 KB processed** |
| IMDb 50K practice corpus (PySpark only) | 50,000 reviews (roughly 11-12 M words; exact count in `outputs/spark/run_info.txt` after the Spark run) | ~63 MB |

Our own data is *small* - every table fits in a spreadsheet. Only the PySpark job (our 145 reviews + the 50K corpus) is "big", and even that fits in a laptop's memory. **Volume did not drive any tool choice except Spark, which the brief required.**

## Velocity
- **Trailer attention** (Wikipedia, daily): Endgame's first trailer day had 165,032 views; by day 3 it was down to 49.5 % of that, Doomsday's trailer (173,712 on day 0) was down to 32.8 % → attention halves in about 2-3 days.
- **Release-day attention**: on 26-Apr-2019 the Endgame page got 1,982,874 views = ~82,600 views per hour, 12× the trailer day.
- **Box office**: Monday after opening = 58 % of Friday for Endgame, 31 % for the 2026 re-release; second weekend = 33 % of the first.
- **Advance booking**: Doomsday Day-1 advance grew from ₹16.48 Cr (19-Nov 02:50) to ₹20.77 Cr (21-Nov 18:50) = **+₹1.6 Cr per day**, 26 days before release.
- **Reviews**: RT reviews of the re-release peaked at 53 per week in its 2nd week (5-11 Oct 2026) and fell to ~10 a week after that.
- We could not measure *comments per hour* on release day for Endgame - YouTube only shows today's cumulative counters, and historical comment timestamps need the API (script ready: `src/collect/youtube_api_collector.py`, run once a day to build real snapshots).

## Variety
JSON from two APIs (Wikimedia, Wikidata) + JSON from YouTube pages, HTML tables (Sacnilk, Bollywood Hungama), text tables (Sacnilk tracker), PDF tables (MoSPI CPI), free text (RT, IMDb), and a labelled CSV corpus. Six different "film name" spellings (e.g. *Avengers: Endgame*, *Avengers End Game*, *Avengers - Official Trailer*, *Avengers Endgame: Encore*, *Q113244839*), four money formats (₹ 53.60 Cr, ₹53.6 cr., ₹37.32 Lac, 2.97 Lac tickets), three date formats (ISO, "26-Apr-2019 (Fri)", "6 days ago").

## Which V dominated, and what it changed
**Variety.** Almost all our time went into making these formats line up on one film key and one unit (₹ crore, dates). That pushed us to:
1. write small, testable parsers (`src/utils.py`) instead of cleaning by hand,
2. keep a **lineage column** (`net_source`) and both trade sources side by side, because they disagree,
3. use a relational model (MySQL) so each source stays its own table and is joined only through `film_id` / dates.

**Velocity came second** and changed *what we measure*: because attention halves within 2-3 days, a single "trailer views" number is meaningless without the date it was taken - so we use daily pageviews for curves and treat YouTube counters as snapshots only.
