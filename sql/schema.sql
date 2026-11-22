-- Release Day Radar - MySQL 8 schema
-- Run:  mysql -u root -p < sql/schema.sql
-- Then: mysql --local-infile=1 -u root -p release_day_radar < sql/load_data.sql

DROP DATABASE IF EXISTS release_day_radar;
CREATE DATABASE release_day_radar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE release_day_radar;

-- one row per film (the clean film key every source is matched to)
CREATE TABLE films (
    film_id             INT PRIMARY KEY,
    film_key            VARCHAR(40)  NOT NULL UNIQUE,
    title               VARCHAR(120) NOT NULL,
    release_date_india  DATE         NOT NULL,
    release_type        VARCHAR(20)  NOT NULL,          -- original / re-release
    parent_film_id      INT NULL,                       -- Encore -> Endgame
    genres              VARCHAR(200),
    runtime_min         INT NULL,
    original_language   VARCHAR(30),
    imdb_id             VARCHAR(15),
    wikidata_id         VARCHAR(15),
    tmdb_id             VARCHAR(15),
    FOREIGN KEY (parent_film_id) REFERENCES films(film_id)
);

-- official CPI (MoSPI); old 2012-base months linked to 2024-base with the published factor
CREATE TABLE cpi_monthly (
    month             DATE PRIMARY KEY,                 -- first day of month
    cpi_base2012      DECIMAL(6,2) NULL,
    cpi_base2024      DECIMAL(6,2) NULL,
    cpi_linked_2024   DECIMAL(6,2) NOT NULL,
    series_used       VARCHAR(40)
);

-- India net box office per day (Sacnilk + Bollywood Hungama)
CREATE TABLE daily_collections (
    film_id              INT  NOT NULL,
    collection_date      DATE NOT NULL,
    day_no               INT  NOT NULL,
    weekday              VARCHAR(10),
    is_weekend           TINYINT(1),
    week_no              INT,
    net_cr               DECIMAL(8,3) NOT NULL,         -- ₹ crore, nominal
    net_source           VARCHAR(30),
    is_approx            TINYINT(1),
    net_cr_sacnilk       DECIMAL(8,3) NULL,
    net_cr_bh            DECIMAL(8,3) NULL,
    net_cr_english       DECIMAL(8,3) NULL,
    net_cr_hindi         DECIMAL(8,3) NULL,
    net_cr_tamil         DECIMAL(8,3) NULL,
    net_cr_telugu        DECIMAL(8,3) NULL,
    gross_cr_est         DECIMAL(8,3) NULL,
    collection_month     DATE NULL,
    cpi_factor_to_target DECIMAL(6,4) NULL,
    net_cr_real          DECIMAL(8,3) NULL,             -- ₹ crore at Oct-2026 prices
    PRIMARY KEY (film_id, collection_date),
    FOREIGN KEY (film_id) REFERENCES films(film_id),
    FOREIGN KEY (collection_month) REFERENCES cpi_monthly(month)
);

-- English Wikipedia daily pageviews (Wikimedia REST API, JSON) = our daily attention signal
CREATE TABLE wiki_pageviews (
    film_id           INT  NOT NULL,
    view_date         DATE NOT NULL,
    project           VARCHAR(30),
    article           VARCHAR(100),
    views             INT  NOT NULL,
    pre_title_reveal  TINYINT(1) DEFAULT 0,
    PRIMARY KEY (film_id, view_date),
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

-- YouTube trailers (cumulative counters at snapshot time, NOT daily history)
CREATE TABLE youtube_videos (
    video_id                 VARCHAR(15) PRIMARY KEY,
    film_id                  INT NOT NULL,
    title                    VARCHAR(200),
    channel                  VARCHAR(60),
    language                 VARCHAR(20),
    published_at             DATETIME,
    duration_sec             INT,
    view_count               BIGINT,
    like_count               BIGINT,
    comment_count            BIGINT NULL,
    days_online_at_snapshot  INT,
    snapshot_taken_at        DATETIME,
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

-- audience reviews (Rotten Tomatoes + IMDb public), usernames never stored
CREATE TABLE reviews (
    review_id                  VARCHAR(60) PRIMARY KEY,
    film_id                    INT NOT NULL,
    source                     VARCHAR(30),
    viewing_context            VARCHAR(40),
    review_date                DATE,
    rating_10                  DECIMAL(4,1) NULL,
    rating_label               VARCHAR(10),
    verified                   TINYINT(1) NULL,
    lang                       VARCHAR(5),
    n_words                    INT,
    is_short                   TINYINT(1),
    is_text_duplicate          TINYINT(1),
    vader_compound             DECIMAL(6,4) NULL,
    model_pos_prob             DECIMAL(6,4) NULL,
    theme_story_plot           TINYINT(1),
    theme_length_pacing        TINYINT(1),
    theme_emotion              TINYINT(1),
    theme_action_vfx           TINYINT(1),
    theme_characters_acting    TINYINT(1),
    theme_extra_scenes_encore  TINYINT(1),
    theme_price_value          TINYINT(1),
    theme_format_experience    TINYINT(1),
    theme_doomsday_hype        TINYINT(1),
    text                       TEXT,
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

-- Doomsday Day-1 advance booking snapshot (Sacnilk), by language / state / city
CREATE TABLE advance_booking (
    booking_row_id     INT PRIMARY KEY,
    film_id            INT NOT NULL,
    snapshot_at        DATETIME,
    show_date          DATE,
    level              VARCHAR(10),                    -- language / state / city
    area               VARCHAR(60),
    gross_cr           DECIMAL(8,4),
    gross_cr_wo_block  DECIMAL(8,4),
    tickets            INT,
    shows              INT,
    occupancy_pct      DECIMAL(5,1) NULL,
    atp_rs             INT NULL,
    atp_rs_derived     INT NULL,
    is_others_bucket   TINYINT(1),
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);

CREATE TABLE release_schedule (
    film_id             INT PRIMARY KEY,
    india_release_date  DATE,
    weekday             VARCHAR(10),
    other_release_note  VARCHAR(200),
    first_show_note     VARCHAR(400),
    show_screen_note    VARCHAR(400),
    source_name         VARCHAR(200),
    source_url          VARCHAR(300),
    FOREIGN KEY (film_id) REFERENCES films(film_id)
);
