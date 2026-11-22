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
       ROUND(SUM(d.net_cr_sacnilk - d.net_cr_bh), 2)   AS signed_gap_cr,
       ROUND(SUM(ABS(d.net_cr_sacnilk - d.net_cr_bh)), 2) AS absolute_gap_cr
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
-- Same nine themes as chart c6. A review can match more than one theme.
SELECT 'extra_scenes_encore' AS theme, SUM(theme_extra_scenes_encore) AS n, ROUND(AVG(CASE WHEN theme_extra_scenes_encore=1 THEN rating_10 END),2) AS avg_rating FROM reviews
UNION ALL SELECT 'format_experience',   SUM(theme_format_experience),   ROUND(AVG(CASE WHEN theme_format_experience=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'doomsday_hype',       SUM(theme_doomsday_hype),       ROUND(AVG(CASE WHEN theme_doomsday_hype=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'emotion',             SUM(theme_emotion),             ROUND(AVG(CASE WHEN theme_emotion=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'story_plot',          SUM(theme_story_plot),          ROUND(AVG(CASE WHEN theme_story_plot=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'characters_acting',   SUM(theme_characters_acting),   ROUND(AVG(CASE WHEN theme_characters_acting=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'length_pacing',       SUM(theme_length_pacing),       ROUND(AVG(CASE WHEN theme_length_pacing=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'action_vfx',          SUM(theme_action_vfx),          ROUND(AVG(CASE WHEN theme_action_vfx=1 THEN rating_10 END),2) FROM reviews
UNION ALL SELECT 'price_value',         SUM(theme_price_value),         ROUND(AVG(CASE WHEN theme_price_value=1 THEN rating_10 END),2) FROM reviews
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

-- Q9 (sentiment vs stars) Does the TF-IDF model agree with the star label, by theme?
-- Cut-offs are the ones in src/s05: probability >= 0.6 positive, <= 0.4 negative, otherwise mixed.
-- Agreement drops mixed stars and mixed model scores, same rule as outputs/tables/sentiment_model_eval.csv.
WITH scored AS (
    SELECT rating_10, rating_label, model_pos_prob,
           CASE WHEN model_pos_prob >= 0.6 THEN 'positive'
                WHEN model_pos_prob <= 0.4 THEN 'negative'
                ELSE 'mixed' END AS model_label,
           theme_story_plot, theme_length_pacing, theme_emotion, theme_action_vfx,
           theme_characters_acting, theme_extra_scenes_encore, theme_price_value,
           theme_format_experience, theme_doomsday_hype
    FROM reviews
    WHERE lang = 'en' AND model_pos_prob IS NOT NULL
),
long AS (
    SELECT 'story_plot' AS theme, theme_story_plot AS hit, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'length_pacing', theme_length_pacing, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'emotion', theme_emotion, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'action_vfx', theme_action_vfx, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'characters_acting', theme_characters_acting, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'extra_scenes_encore', theme_extra_scenes_encore, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'price_value', theme_price_value, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'format_experience', theme_format_experience, rating_10, rating_label, model_label, model_pos_prob FROM scored
    UNION ALL SELECT 'doomsday_hype', theme_doomsday_hype, rating_10, rating_label, model_label, model_pos_prob FROM scored
),
by_theme AS (
    SELECT theme,
           SUM(hit) AS n,
           SUM(CASE WHEN hit = 1 AND rating_label IN ('positive','negative') AND model_label IN ('positive','negative') THEN 1 ELSE 0 END) AS n_compared,
           SUM(CASE WHEN hit = 1 AND rating_label IN ('positive','negative') AND model_label = rating_label THEN 1 ELSE 0 END) AS n_agree,
           AVG(CASE WHEN hit = 1 THEN rating_10 END) AS avg_rating,
           AVG(CASE WHEN hit = 1 THEN model_pos_prob END) AS avg_model_pos_prob
    FROM long
    GROUP BY theme
),
overall AS (
    SELECT 'ALL_ENGLISH' AS theme,
           COUNT(*) AS n,
           SUM(CASE WHEN rating_label IN ('positive','negative') AND model_label IN ('positive','negative') THEN 1 ELSE 0 END) AS n_compared,
           SUM(CASE WHEN rating_label IN ('positive','negative') AND model_label = rating_label THEN 1 ELSE 0 END) AS n_agree,
           AVG(rating_10) AS avg_rating,
           AVG(model_pos_prob) AS avg_model_pos_prob
    FROM scored
)
SELECT theme, n, n_compared,
       ROUND(100.0 * n_agree / NULLIF(n_compared, 0), 1) AS agree_pct,
       ROUND(avg_rating, 2) AS avg_rating,
       ROUND(avg_model_pos_prob, 3) AS avg_model_pos_prob
FROM (
    SELECT * FROM by_theme
    UNION ALL
    SELECT * FROM overall
) u
ORDER BY CASE WHEN theme = 'ALL_ENGLISH' THEN 1 ELSE 0 END, avg_rating;
