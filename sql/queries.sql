-- Release Day Radar - analysis queries (MySQL 8)
-- mysql -u root -p release_day_radar < sql/queries.sql
-- Each query answers one small question we needed for the report.

USE release_day_radar;

-- Q1 (JOIN + GROUP BY) Weekly India net per film, nominal vs inflation-adjusted (Oct-2026 ₹)
SELECT f.title,
       d.week_no,
       COUNT(*)                     AS days_in_week,
       ROUND(SUM(d.net_cr), 2)      AS net_cr_nominal,
       ROUND(SUM(d.net_cr_real), 2) AS net_cr_oct2026_prices
FROM daily_collections d
JOIN films f ON f.film_id = d.film_id
GROUP BY f.title, d.week_no
ORDER BY f.title, d.week_no;

-- Q2 (JOIN on 3 tables) Opening weekend: box office next to Wikipedia attention on the same days
SELECT f.title,
       d.collection_date,
       d.weekday,
       d.net_cr,
       w.views AS wiki_views,
       ROUND(d.net_cr * 1e7 / w.views, 1) AS rupees_net_per_wiki_view
FROM daily_collections d
JOIN films f          ON f.film_id = d.film_id
JOIN wiki_pageviews w ON w.film_id = d.film_id AND w.view_date = d.collection_date
WHERE d.day_no <= 3
ORDER BY f.title, d.collection_date;

-- Q3 (GROUP BY + HAVING) Where do the two trade sources disagree, and by how much in total?
SELECT d.week_no,
       COUNT(*)                                        AS days_compared,
       SUM(CASE WHEN d.net_cr_sacnilk <> d.net_cr_bh THEN 1 ELSE 0 END) AS days_disagree,
       ROUND(SUM(d.net_cr_sacnilk - d.net_cr_bh), 2)   AS total_gap_cr
FROM daily_collections d
WHERE d.net_cr_sacnilk IS NOT NULL AND d.net_cr_bh IS NOT NULL
GROUP BY d.week_no
HAVING days_compared > 0
ORDER BY d.week_no;

-- Q4 (window function) Trailer attention decay: views on each of the first 14 days after the trailer,
--     as % of day-0 views, for both films side by side
WITH day0 AS (
    SELECT 1 AS film_id, DATE '2018-12-07' AS d0 UNION ALL
    SELECT 3,           DATE '2026-07-20'
),
win AS (
    SELECT w.film_id, DATEDIFF(w.view_date, day0.d0) AS day_since_trailer, w.views
    FROM wiki_pageviews w JOIN day0 ON day0.film_id = w.film_id
    WHERE w.view_date BETWEEN day0.d0 AND DATE_ADD(day0.d0, INTERVAL 13 DAY)
)
SELECT f.title, win.day_since_trailer, win.views,
       ROUND(100.0 * win.views / FIRST_VALUE(win.views) OVER (PARTITION BY win.film_id ORDER BY win.day_since_trailer), 1)
           AS pct_of_day0
FROM win JOIN films f ON f.film_id = win.film_id
ORDER BY win.day_since_trailer, f.title;

-- Q5 (JOIN + GROUP BY) YouTube trailers: total views/likes per film and language (snapshot counters)
SELECT f.title, y.language,
       COUNT(*)                                         AS n_videos,
       SUM(y.view_count)                                AS total_views,
       ROUND(100.0 * SUM(y.like_count) / SUM(y.view_count), 2) AS like_rate_pct
FROM youtube_videos y
JOIN films f ON f.film_id = y.film_id
GROUP BY f.title, y.language
ORDER BY total_views DESC;

-- Q6 (GROUP BY) What do reviewers talk about, and how do those reviews rate?
SELECT 'price_value'      AS theme, SUM(theme_price_value) AS n, ROUND(AVG(CASE WHEN theme_price_value=1 THEN rating_10 END),2) AS avg_rating FROM reviews
UNION ALL SELECT 'extra_scenes_encore', SUM(theme_extra_scenes_encore), ROUND(AVG(CASE WHEN theme_extra_scenes_encore=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'emotion',            SUM(theme_emotion),             ROUND(AVG(CASE WHEN theme_emotion=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'length_pacing',      SUM(theme_length_pacing),       ROUND(AVG(CASE WHEN theme_length_pacing=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'doomsday_hype',      SUM(theme_doomsday_hype),       ROUND(AVG(CASE WHEN theme_doomsday_hype=1 THEN rating_10 END),2) FROM reviews
ORDER BY n DESC;

-- Q7 (subquery) Doomsday advance: states whose gross per show beats the all-India average
SELECT a.area AS state, a.gross_cr, a.shows, a.occupancy_pct,
       ROUND(a.gross_cr * 100 / a.shows, 2) AS gross_lakh_per_show
FROM advance_booking a
WHERE a.level = 'state' AND a.is_others_bucket = 0
  AND a.gross_cr / a.shows > (SELECT gross_cr / shows FROM advance_booking WHERE level = 'language' AND area = 'All India')
ORDER BY gross_lakh_per_show DESC;

-- Q8 (JOIN to CPI) How much of the "real" uplift comes from inflation, month by month
SELECT f.title, c.month, c.series_used, c.cpi_linked_2024,
       ROUND(SUM(d.net_cr), 2) AS net_cr_nominal, ROUND(SUM(d.net_cr_real), 2) AS net_cr_real
FROM daily_collections d
JOIN cpi_monthly c ON c.month = d.collection_month
JOIN films f       ON f.film_id = d.film_id
GROUP BY f.title, c.month, c.series_used, c.cpi_linked_2024
ORDER BY c.month;
