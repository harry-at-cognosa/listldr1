# Project Structure — listldr (SQM Template Loader)

## Overview

A system for loading, storing, and managing industrial sales-quote template Word documents (.docx). Templates are parsed into discrete sections, stored in a PostgreSQL database, and served via a REST API. The project is evolving toward a template migration capability (CHE→USA regional conversion).

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12 |
| Web framework | FastAPI | ≥ 0.115 |
| ASGI server | Uvicorn | ≥ 0.32 |
| Database | PostgreSQL | 17.x |
| DB driver | psycopg2-binary | ≥ 2.9 |
| DB migrations | Alembic + SQLAlchemy | ≥ 1.13 / ≥ 2.0 |
| Document parsing | python-docx | ≥ 1.1 |
| Document assembly | docxcompose | ≥ 1.4 |
| Excel support | openpyxl | ≥ 3.1 |
| Environment config | python-dotenv | ≥ 1.0 |
| Connection pooling | psycopg2 ThreadedConnectionPool | — |

**Extensions:** PostgreSQL `btree_gist` and `pgcrypto` (SHA-256 blob deduplication).

---

## Directory Layout

```
1_listldr/
├── listldr/                  # Shared library package
│   ├── __init__.py
│   ├── db.py                 #   SQMDatabase class — all DB operations
│   ├── parser.py             #   Docx parsing, section extraction, TOC validation
│   ├── service.py            #   load_template() orchestration (parse → match → store)
│   ├── models.py             #   Dataclasses (LoadResult, SectionInfo, etc.)
│   ├── config.py             #   DBConfig, db_config_from_env()
│   ├── logger.py             #   Dual-output logging (file + console)
│   └── text_utils.py         #   LCS algorithm, text normalisation helpers
│
├── api/                      # FastAPI REST API
│   ├── __init__.py
│   ├── app.py                #   App factory, lifespan (pool + cached lookups)
│   ├── routes.py             #   POST /load, GET /sections/{seqn}/docx
│   ├── schemas.py            #   Pydantic response models
│   └── dependencies.py       #   Dependency injection (get_db, get_section_types)
│
├── cli/                      # CLI programs
│   ├── __init__.py
│   ├── batch_load.py         #   Batch template loader (reads INI config, processes folder)
│   └── archive_blobs.py      #   Blob archive/cleanup utility
│
├── conf/                     # Configuration
│   └── listldr_sqt.ini       #   Batch loader config (paths, country, DB credentials)
│
├── docs/                     # Documentation (specs, design docs, analysis)
├── templates_docx/           # Source .docx template files (CHE + USA samples)
├── templates_xlsx/           # Companion Excel files
├── inputs/                   # Batch processing input folder
├── outputs/                  # Processing output folder
├── reports/                  # Generated reports
├── log/                      # Log files (gitignored)
├── sql_files/                # Ad-hoc SQL scripts
├── alembic/                  # DB migration framework
│   └── versions/             #   Migration version files
│
├── SQM_load_quote_template_docx_file_v2.0.py   # Shim → cli.batch_load.main()
├── poc_section_swap.py       # POC: extract/replace sections at XML level
├── poc_docxcompose.py        # POC: assemble documents from section files
├── requirements.txt
├── alembic.ini
├── .env / .env.example       # API environment variables
└── .gitignore
```

---

## Database — `listmgr1`

PostgreSQL 17.x, 15 tables.

### Core Tables

| Table | Purpose |
|-------|---------|
| `plsq_templates` | Template master records (name, country, currency, product line, section count, status) |
| `plsqt_sections` | Template sections (sequence number, section type, content text, alt name) |
| `plsqts_type` | 17 section type definitions (e.g. "Product Pump", "Cover Page - CH/EU") |
| `document_blob` | Binary .docx storage, deduplicated by SHA-256 hash |
| `document_blob_history` | Blob version archive (entity type, entity ID, prior blob references) |

### Reference Tables

| Table | Purpose |
|-------|---------|
| `country` | Country codes (CHE, USA, etc.) with default currency FK |
| `currency` | Currency codes (CHF, USD, EUR) |
| `product_cat` | Product categories |
| `product_line` | Product lines (UBM, ECM, KD, etc.) within categories |

### Price Conversion Tables

| Table | Purpose |
|-------|---------|
| `country_conversion_pairs` | Defines migration paths (CHE→USA) |
| `price_conv_factors` | Factor types: FX (currency exchange), MU (markup/duties) |
| `pconv_factor_values` | Active factor values by date range and conversion pair |

### Other Tables

| Table | Purpose |
|-------|---------|
| `customer_quotes` | Customer quote tracking |
| `users` | Application users |
| `app_settings` | Key-value application settings |

---

## API Endpoints

Base: `http://localhost:8000/api/v1/templates`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/load` | Upload and parse a .docx template into the database |
| GET | `/{plsqt_id}/sections/{seqn}/docx` | Extract a single section as a formatted .docx file |

Start with: `uvicorn api.app:app --reload`

Configuration via `.env` (see `.env.example`).

---

## CLI Programs

### Batch Template Loader

```bash
python SQM_load_quote_template_docx_file_v2.0.py
```

Reads `conf/listldr_sqt.ini`, processes all `.docx` files in the configured input folder. For each file:

1. Parse sections using TOC-driven validation
2. Match section types via LCS (longest common substring) algorithm
3. Store/deduplicate blob (SHA-256)
4. Insert/update template and section records
5. Transaction-based with per-file rollback on error

### Blob Archive Utility

```bash
python -m cli.archive_blobs
```

Archives and cleans up orphaned or superseded document blobs.

---

## Key Design Patterns

- **Shared library (`listldr/`)**: All business logic lives here; API and CLI are thin callers
- **Connection injection**: `SQMDatabase.__init__` accepts an optional `conn` parameter for pool-based usage (API) or standalone connections (CLI)
- **Caller-managed transactions**: `load_template()` does not commit — the API or CLI caller controls commit/rollback
- **LCS section-type matching**: Robust fuzzy matching (min 4-char common substring) handles section title variations across product lines
- **TOC-driven validation**: Section sequence validated against the cover page's table of contents rather than hardcoded per-product rules
- **Blob deduplication**: SHA-256 hash prevents duplicate storage; `document_blob_history` tracks version lineage

---

## Configuration

### Batch CLI — `conf/listldr_sqt.ini`

```ini
[paths]         # Input folder, log directory
[template]      # Source country/currency, log slug
[processing]    # Skip/limit counts, error handling flags
[database]      # PostgreSQL connection parameters
```

### API — `.env`

```
LISTLDR_DB_HOST, LISTLDR_DB_PORT, LISTLDR_DB_USER,
LISTLDR_DB_PASSWORD, LISTLDR_DB_NAME, LISTLDR_CORS_ORIGINS
```

---

## Current State and Roadmap

### Implemented

- CHE template import pipeline (batch CLI + API)
- Section extraction and database storage
- Section-as-docx extraction endpoint
- Blob versioning and archive
- Price conversion factor infrastructure (DB tables populated, no application code yet)
- POC code for section swap and document assembly

### In Progress

- CHE→USA template migration analysis (6 sample templates compared across all sections)
- Identifying generic vs product-line-specific transformation rules

### Planned

- Template migration function (text/format conversion, then price conversion)
- Section-level text replacement rules engine
- Document assembly from transformed sections
