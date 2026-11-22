-- Load the processed CSVs into MySQL.
-- Run from the PROJECT ROOT folder (paths below are relative to it):
--   mysql --local-infile=1 -u root -p release_day_radar < sql/load_data.sql
-- If MySQL complains about local_infile:  SET GLOBAL local_infile = 1;  (as root, once)
-- Empty CSV fields become NULL through the NULLIF(@x,'') pattern.

USE release_day_radar;
SET FOREIGN_KEY_CHECKS = 0;

LOAD DATA LOCAL INFILE 'data/processed/films.csv' INTO TABLE films
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(film_id, film_key, title, release_date_india, release_type, @parent, genres, @runtime, original_language, @imdb, @wd, @tmdb)
SET parent_film_id = NULLIF(@parent,''), runtime_min = NULLIF(@runtime,''),
    imdb_id = NULLIF(@imdb,''), wikidata_id = NULLIF(@wd,''), tmdb_id = NULLIF(@tmdb,'');

LOAD DATA LOCAL INFILE 'data/processed/cpi_monthly.csv' INTO TABLE cpi_monthly
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(month, @old, @new, cpi_linked_2024, series_used)
SET cpi_base2012 = NULLIF(@old,''), cpi_base2024 = NULLIF(@new,'');

LOAD DATA LOCAL INFILE 'data/processed/daily_collections.csv' INTO TABLE daily_collections
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(film_id, collection_date, day_no, weekday, is_weekend, week_no, net_cr, net_source, is_approx,
 @sac, @bh, @en, @hi, @ta, @te, @gross, @cm, @factor, @real)
SET net_cr_sacnilk = NULLIF(@sac,''), net_cr_bh = NULLIF(@bh,''), net_cr_english = NULLIF(@en,''),
    net_cr_hindi = NULLIF(@hi,''), net_cr_tamil = NULLIF(@ta,''), net_cr_telugu = NULLIF(@te,''),
    gross_cr_est = NULLIF(@gross,''), collection_month = NULLIF(@cm,''),
    cpi_factor_to_target = NULLIF(@factor,''), net_cr_real = NULLIF(@real,'');

LOAD DATA LOCAL INFILE 'data/processed/wiki_pageviews.csv' INTO TABLE wiki_pageviews
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(film_id, view_date, project, article, views, pre_title_reveal);

LOAD DATA LOCAL INFILE 'data/processed/youtube_videos.csv' INTO TABLE youtube_videos
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(video_id, film_id, title, channel, language, published_at, duration_sec, view_count, like_count, @cc,
 days_online_at_snapshot, snapshot_taken_at)
SET comment_count = NULLIF(@cc,'');

LOAD DATA LOCAL INFILE 'data/processed/reviews.csv' INTO TABLE reviews
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES
(review_id, film_id, source, viewing_context, review_date, @rating, rating_label, @verified, lang, n_words,
 is_short, is_text_duplicate, @vader, @prob, theme_story_plot, theme_length_pacing, theme_emotion, theme_action_vfx,
 theme_characters_acting, theme_extra_scenes_encore, theme_price_value, theme_format_experience, theme_doomsday_hype, text)
SET rating_10 = NULLIF(@rating,''), verified = NULLIF(@verified,''),
    vader_compound = NULLIF(@vader,''), model_pos_prob = NULLIF(@prob,'');

LOAD DATA LOCAL INFILE 'data/processed/advance_booking.csv' INTO TABLE advance_booking
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(booking_row_id, film_id, snapshot_at, show_date, level, area, gross_cr, gross_cr_wo_block, tickets, shows,
 @occ, @atp, @atpd, is_others_bucket)
SET occupancy_pct = NULLIF(@occ,''), atp_rs = NULLIF(@atp,''), atp_rs_derived = NULLIF(@atpd,'');

LOAD DATA LOCAL INFILE 'data/processed/release_schedule.csv' INTO TABLE release_schedule
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
(film_id, india_release_date, weekday, other_release_note, first_show_note, show_screen_note, source_name, source_url);

SET FOREIGN_KEY_CHECKS = 1;

-- row counts (compare with the README table)
SELECT 'films' t, COUNT(*) n FROM films UNION ALL
SELECT 'cpi_monthly', COUNT(*) FROM cpi_monthly UNION ALL
SELECT 'daily_collections', COUNT(*) FROM daily_collections UNION ALL
SELECT 'wiki_pageviews', COUNT(*) FROM wiki_pageviews UNION ALL
SELECT 'youtube_videos', COUNT(*) FROM youtube_videos UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews UNION ALL
SELECT 'advance_booking', COUNT(*) FROM advance_booking UNION ALL
SELECT 'release_schedule', COUNT(*) FROM release_schedule;
