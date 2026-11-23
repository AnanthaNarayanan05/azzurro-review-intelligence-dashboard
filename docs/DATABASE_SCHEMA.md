# Database Schema

Status: Proposed (Phase 1). Will be adapted once the real export's columns are known.
Implemented with SQLAlchemy 2.0; migrations via Alembic. Types below are portable between SQLite and PostgreSQL.

## Entity relationships

```
properties 1───* property_aliases
properties 1───* reviews *───1 import_batches 1───* import_row_issues
reviews    1───* sentiment_results *───1 analysis_runs
reviews    1───* aspect_mentions   *───1 aspects
                 aspect_mentions   *───1 analysis_runs
insights   *───* properties  (insight_properties)
insights   *───* reviews     (insight_evidence)
insights   *───1 analysis_runs
```

## Tables

### properties
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| code | VARCHAR(32) | UNIQUE, NOT NULL (short slug used in URLs) |
| name | VARCHAR(200) | UNIQUE, NOT NULL |
| location | VARCHAR(200) | NULL (only if supplied) |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at / updated_at | TIMESTAMP | NOT NULL |

### property_aliases
Maps raw property values found in source files to a property.
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| property_id | INTEGER | FK → properties.id ON DELETE CASCADE |
| alias_normalised | VARCHAR(200) | UNIQUE, NOT NULL (lower-cased, trimmed, whitespace-collapsed) |

### import_batches
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| filename | VARCHAR(255) | NOT NULL (original name, sanitised) |
| file_sha256 | CHAR(64) | NOT NULL, indexed (warns on re-upload of identical file) |
| source_type | VARCHAR(32) | NOT NULL (`csv`, `xlsx`, future `api`) |
| source_name | VARCHAR(64) | NOT NULL, default `booking.com` |
| column_mapping | JSON | NOT NULL (source column → internal field) |
| rating_scale_max | NUMERIC(4,1) | NOT NULL, default 10 |
| status | VARCHAR(16) | NOT NULL, CHECK IN (`previewed`,`processing`,`completed`,`failed`) |
| total_rows / imported_rows / updated_rows / rejected_rows / duplicate_rows | INTEGER | NOT NULL, default 0 (`updated_rows` added in Phase 3) |
| import_options | JSON | NOT NULL, default `{}` (date format, property mapping, sheet, alias choice; Phase 3) |
| stored_filename | VARCHAR(255) | NULL. Name of the private copy in `data/uploads`; set only between preview and commit, cleared after (Phase 3) |
| error_message | TEXT | NULL. Why a `failed` import was rolled back (Phase 3) |
| is_synthetic | BOOLEAN | NOT NULL, default false |
| created_at / completed_at | TIMESTAMP | |

Invariant (tested): `total_rows = imported_rows + updated_rows + rejected_rows + duplicate_rows`.

### import_row_issues
Every non-imported row is recorded here – nothing is silently discarded.
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| import_id | INTEGER | FK → import_batches.id ON DELETE CASCADE, indexed |
| row_number | INTEGER | NOT NULL (1-based, as in the source file) |
| outcome | VARCHAR(16) | CHECK IN (`rejected`,`duplicate`,`warning`) |
| field | VARCHAR(64) | NULL |
| code | VARCHAR(48) | NOT NULL. The implemented codes are listed in `API_SPECIFICATION.md` (e.g. `INVALID_DATE`, `RATING_OUT_OF_RANGE`, `UNKNOWN_PROPERTY`, `EMPTY_REVIEW`, `DUPLICATE_IN_FILE`, `DUPLICATE_EXTERNAL_ID`, `DUPLICATE_CONTENT`) |
| message | VARCHAR(500) | NOT NULL |
| duplicate_of_review_id | INTEGER | NULL, FK → reviews.id |

Warnings (e.g. missing language, rating missing but text present) do not block import.

### reviews
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK (internal) |
| external_review_id | VARCHAR(128) | NULL (source's own ID, if supplied) |
| property_id | INTEGER | FK → properties.id, NOT NULL |
| import_id | INTEGER | FK → import_batches.id, NOT NULL |
| source | VARCHAR(64) | NOT NULL, default `booking.com` |
| review_date | DATE | NOT NULL |
| rating | NUMERIC(4,2) | NULL, CHECK (rating IS NULL OR rating BETWEEN 0 AND 10) – normalised to a /10 scale |
| rating_raw | NUMERIC(6,2) | NULL (as in source) |
| title | TEXT | NULL |
| positive_text | TEXT | NULL (original, unmodified) |
| negative_text | TEXT | NULL (original, unmodified) |
| body_text | TEXT | NULL (for sources with a single text field) |
| language | VARCHAR(8) | NULL (source value or detected) |
| language_detected | BOOLEAN | NOT NULL, default false |
| traveller_type / reviewer_country / room_type | VARCHAR(100) | NULL, only if provided |
| stay_nights | INTEGER | NULL |
| extra | JSON | NULL. Reserved for audit of unmapped columns. **Not populated in Phase 3**: unmapped columns are deliberately discarded (data minimisation) |
| content_hash | CHAR(64) | NOT NULL. SHA-256 of source, property id, date, rating (2 decimals) and the normalised title, positive, negative and body text. Source is included so a synthetic review can never collide with a genuine one |
| is_synthetic | BOOLEAN | NOT NULL, default false |
| source_url | TEXT | NULL. Optional link to the review at its source, only if the file supplies one (Phase 3) |
| imported_at | TIMESTAMP | NOT NULL |
| updated_at | TIMESTAMP | NULL. Set when a re-import changes an existing review in place (Phase 3) |
| analysis_status | VARCHAR(16) | NULL, CHECK IN (`analysed`,`no_text`,`non_english`), indexed (Phase 4). NULL = waiting to be analysed. A re-import that changes the review's content resets it to NULL so it is re-scored |
| analysed_run_id | INTEGER | NULL, FK → analysis_runs.id ON DELETE SET NULL (Phase 4). The run that produced the review's current results |

Constraints / indexes:
- CHECK: at least one of `positive_text`, `negative_text`, `body_text`, `rating` is non-null.
- UNIQUE (`source`, `external_review_id`) – when an external ID exists (partial index on PostgreSQL; enforced in application logic on SQLite as well).
- UNIQUE (`content_hash`) – fallback duplicate detection when no external ID exists.
- INDEX (`property_id`, `review_date`), INDEX (`review_date`), INDEX (`rating`).

### analysis_runs
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| triggered_by | VARCHAR(16) | `import` / `manual` |
| sentiment_engine | VARCHAR(64) | NOT NULL (e.g. `vader-3.3.2`) |
| aspect_lexicon_version | VARCHAR(32) | NOT NULL |
| reviews_processed | INTEGER | NOT NULL |
| status | VARCHAR(16) | `running` / `completed` / `failed` |
| started_at / completed_at | TIMESTAMP | |

### sentiment_results
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| review_id | INTEGER | FK → reviews.id ON DELETE CASCADE |
| analysis_run_id | INTEGER | FK → analysis_runs.id |
| segment | VARCHAR(16) | CHECK IN (`overall`,`positive`,`negative`,`body`) |
| label | VARCHAR(8) | CHECK IN (`positive`,`neutral`,`negative`) |
| score | NUMERIC(6,4) | NOT NULL (e.g. VADER compound −1…1) |
| confidence | NUMERIC(5,4) | NULL (where the model provides one) |
| model_name | VARCHAR(64) | NOT NULL |
| analysed_at | TIMESTAMP | NOT NULL |

UNIQUE (`review_id`, `segment`, `model_name`); INDEX (`segment`, `label`).
Reviews with no usable text get no `overall` row and are reported as "no text" rather than "neutral".

### aspects
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| key | VARCHAR(48) | UNIQUE (e.g. `cleanliness`) |
| display_name | VARCHAR(100) | NOT NULL |
| is_active | BOOLEAN | default true |

Keyword definitions live in a versioned JSON file (`backend/app/analytics/nlp/aspect_lexicon.json`, Phase 4).
Each analysis run syncs it to this table: new aspects are added, and an aspect removed from the file is set to
`is_active = false` (its history is kept, it is no longer reported). Aspects can be extended without code changes.

### aspect_mentions
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| review_id | INTEGER | FK → reviews.id ON DELETE CASCADE |
| aspect_id | INTEGER | FK → aspects.id |
| analysis_run_id | INTEGER | FK → analysis_runs.id |
| source_field | VARCHAR(16) | `positive` / `negative` / `body` / `title` |
| sentiment_label | VARCHAR(8) | CHECK IN (`positive`,`neutral`,`negative`) |
| score | NUMERIC(6,4) | NOT NULL |
| evidence_text | TEXT | NOT NULL (the sentence that triggered the match, verbatim) |
| matched_term | VARCHAR(100) | NOT NULL (explainability) |

INDEX (`aspect_id`, `sentiment_label`), INDEX (`review_id`).
A review counts **once per aspect** in mention counts (multiple sentences about the same aspect are
aggregated); the individual sentences are kept as evidence.

### insights
| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| analysis_run_id | INTEGER | FK → analysis_runs.id |
| insight_type | VARCHAR(32) | CHECK IN (`recurring_complaint`,`strength`,`emerging_negative_trend`,`property_issue`,`cross_property_issue`,`opportunity`) |
| scope | VARCHAR(16) | `portfolio` / `property` / `multi_property` |
| aspect_id | INTEGER | NULL, FK → aspects.id |
| title | VARCHAR(200) | NOT NULL |
| explanation | TEXT | NOT NULL |
| recommended_action | TEXT | NOT NULL |
| supporting_review_count | INTEGER | NOT NULL |
| period_start / period_end | DATE | NOT NULL |
| evidence_strength | VARCHAR(8) | CHECK IN (`strong`,`moderate`,`limited`) |
| metrics | JSON | NOT NULL (the exact computed numbers the text refers to) |
| generation_method | VARCHAR(16) | `template` / `llm` |
| llm_model | VARCHAR(64) | NULL |
| generated_at | TIMESTAMP | NOT NULL |

### insight_properties
(`insight_id` FK, `property_id` FK) – composite PK.

### insight_evidence
(`insight_id` FK, `review_id` FK, `excerpt` TEXT, `rank` INTEGER) – composite PK (`insight_id`, `review_id`).
`supporting_review_count` is the full count; `insight_evidence` stores a ranked sample of example reviews
(e.g. up to 10), and the full supporting set is reproducible from the stored metrics query.

## Data integrity notes

- Deleting an import batch cascades to its reviews and their analysis (supports "undo import").
- Foreign keys are enforced on SQLite via `PRAGMA foreign_keys=ON`.
- All timestamps stored in UTC.
