# ER diagram



```mermaid
erDiagram
    FILMS ||--o{ DAILY_COLLECTIONS : "earns"
    FILMS ||--o{ WIKI_PAGEVIEWS : "gets attention"
    FILMS ||--o{ YOUTUBE_VIDEOS : "has trailers"
    FILMS ||--o{ REVIEWS : "is reviewed in"
    FILMS ||--o{ ADVANCE_BOOKING : "pre-sells"
    FILMS ||--o| RELEASE_SCHEDULE : "opens on"
    FILMS |o--o{ FILMS : "re-release of"
    CPI_MONTHLY ||--o{ DAILY_COLLECTIONS : "deflates"

    FILMS {
        int film_id PK
        varchar film_key UK
        varchar title
        date release_date_india
        varchar release_type
        int parent_film_id FK
        varchar genres
        int runtime_min
        varchar imdb_id
        varchar wikidata_id
        varchar tmdb_id
    }
    DAILY_COLLECTIONS {
        int film_id PK, FK
        date collection_date PK
        int day_no
        int week_no
        decimal net_cr
        varchar net_source
        decimal net_cr_sacnilk
        decimal net_cr_bh
        decimal gross_cr_est
        date collection_month FK
        decimal net_cr_real
    }
    CPI_MONTHLY {
        date month PK
        decimal cpi_base2012
        decimal cpi_base2024
        decimal cpi_linked_2024
    }
    WIKI_PAGEVIEWS {
        int film_id PK, FK
        date view_date PK
        int views
        tinyint pre_title_reveal
    }
    YOUTUBE_VIDEOS {
        varchar video_id PK
        int film_id FK
        varchar channel
        varchar language
        datetime published_at
        bigint view_count
        bigint like_count
        datetime snapshot_taken_at
    }
    REVIEWS {
        varchar review_id PK
        int film_id FK
        varchar source
        date review_date
        decimal rating_10
        varchar rating_label
        text text
    }
    ADVANCE_BOOKING {
        int booking_row_id PK
        int film_id FK
        datetime snapshot_at
        varchar level
        varchar area
        decimal gross_cr
        int tickets
        int shows
        decimal occupancy_pct
    }
    RELEASE_SCHEDULE {
        int film_id PK, FK
        date india_release_date
        varchar first_show_note
    }
```

Design notes
- `film_key` is the cleaned title key; all raw spellings are mapped to it in `src/utils.py::match_film`.
- `daily_collections` has a composite key (film, date) - one number per film per day; both trade sources are kept as columns, `net_cr` is the chosen value and `net_source` says where it came from.
- `collection_month → cpi_monthly.month` is how inflation adjustment is joined (query Q8). It is NULL for Nov-2026 days because that CPI is not published yet.
- `films.parent_film_id` links the Encore re-release to the original film.
