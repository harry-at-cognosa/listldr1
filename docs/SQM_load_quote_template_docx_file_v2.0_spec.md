# SQM Load Quote Template v2.0 — Program Specification

**Program:** `SQM_load_quote_template_docx_file_v2.0.py`
**Version:** 2.1
**Database:** `listmgr1` (PostgreSQL 17, public schema)
**Spec revision:** v1 — 2026-02-06

---

## 1  Purpose

Read one or more WAB sales-quote template files (`.docx`) from a local directory, parse each file into its constituent sections, and store the results in the `listmgr1` database. The input files are **Swiss (CHE) originals** in CHF. A separate, future program will generate converted (e.g. USA/USD) templates.

| Target table | One row per... |
|---|---|
| `plsq_templates` | template file |
| `plsqt_sections` | section within a template |
| `document_blob` | original `.docx` binary |
| `document_blob_history` | (written when an existing blob is replaced) |

Section types are resolved against the existing `plsqts_type` lookup table; they are **not** created by this program.

### 1.1  Changes from v1

| Area | v1 (`SQM_load_quote_template_docx_file.py`) | v2.0 |
|---|---|---|
| Section-type matching | 12-character prefix match (`LOWER(LEFT(...,12))`) against `plsqts_type` via SQL query per heading | **Longest-common-substring (LCS)** match against a pre-fetched in-memory list of all section types |
| Section sequence validation | Hardcoded expected sequences per product line (`ECM`, `UBM`, `KD`) | **TOC-driven**: expected sequence derived from the cover page table of contents |
| File discovery filter | All `.docx` files in directory | Excludes Word temp files (`~$...`) and iCloud numeric-name artifacts |
| Version | `0.01` | `2.1` |

---

## 2  Runtime Configuration

Configuration values are read from an INI file (`listldr_sqt.ini`) and may be overridden by command-line arguments. Command-line arguments take precedence.

### 2.1  Configuration Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `PATH_ROOT` | path | *(required)* | Root of the file tree (e.g. `/Users/harry/1_listldr_files`). |
| `TEMPLATE_INPUT_FOLDER` | path | `inputs/che` | Folder (relative to `PATH_ROOT`) containing source `.docx` files. |
| `TEMPLATE_COUNTRY_IN` | char(3) | `CHE` | Source-country abbreviation. Must match `country.country_abbr`. |
| `TEMPLATE_CURRENCY_IN` | char(3) | `CHF` | Source-currency symbol. Must match `currency.currency_symbol`. |
| `LOGFILE_DIR_PATH` | path | `./log` | Directory for log files. |
| `LOG_FILENAME_SLUG` | string | `load_templates` | Embedded in the log-file name. |
| `NUM_TO_SKIP` | int >= 0 | `0` | Number of files to skip (alphabetical order) before processing begins. |
| `NUM_TO_PROCESS` | int >= 0 | `0` | Maximum files to process. `0` = no limit (process all). |
| `NOUPDATE` | bool | `false` | When `true`, all database writes are suppressed; parsing and logging still occur (dry-run mode). |
| `CONTINUE_ON_ERRORS` | bool | `true` | When `true`, a file-level error is logged and the program advances to the next file. When `false`, the program halts on the first error. |
| `SILENT` | bool | `false` | When `true`, only start/stop messages and progress indicators (`T`, `S`) are written to the console; all other detail goes to the log file only. |

### 2.2  Command-Line Arguments

```
python SQM_load_quote_template_docx_file_v2.0.py [options]
```

| Argument | Maps to | Description |
|---|---|---|
| `--ini PATH` | *(config file)* | Config file path (default: `./conf/listldr_sqt.ini`) |
| `--path-root PATH` | `PATH_ROOT` | Override root path |
| `--input-folder PATH` | `TEMPLATE_INPUT_FOLDER` | Override input folder |
| `--country CODE` | `TEMPLATE_COUNTRY_IN` | Override source country |
| `--currency CODE` | `TEMPLATE_CURRENCY_IN` | Override source currency |
| `--skip N` | `NUM_TO_SKIP` | Number of files to skip |
| `--process N` | `NUM_TO_PROCESS` | Max files to process (0 = all) |
| `--noupdate` | `NOUPDATE=true` | Dry-run mode |
| `--no-continue` | `CONTINUE_ON_ERRORS=false` | Halt on first error |
| `--silent` | `SILENT=true` | Suppress console detail |

### 2.3  Database Connection

| Setting | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| User | `postgres` |
| Password | *(none)* |
| Database | `listmgr1` |
| Library | `psycopg2` |

---

## 3  Processing Overview

```
Initialise  ->  Discover files  ->  For each file:  ->  Finalise
                                      Parse metadata
                                      Parse sections
                                      Validate via TOC
                                      Match section types (LCS)
                                      Store to DB (unless NOUPDATE)
```

### 3.1  Initialise

1. Read INI file; apply command-line overrides.
2. Open the log file (see S5).
3. Log the start-of-run message including program version, start timestamp, input folder, and source country/currency.
4. Connect to the database.
5. Look up and cache the `country_id` and `currency_id` for the configured source country and currency.
6. **Pre-fetch all section types** from `plsqts_type` into an in-memory list of `(plsqtst_id, plsqtst_name)` tuples, ordered by `plsqtst_id ASC`. This list is reused for LCS matching across all files.

### 3.2  Discover Files

1. List all `.docx` files in `TEMPLATE_INPUT_FOLDER`.
2. **Exclude** files whose name starts with `~` (Word temp files) and files whose stem is purely numeric (iCloud sync artifacts).
3. Sort alphabetically (case-insensitive).
4. If no files are found, log the fact and exit.
5. Log the count of files found.
6. Apply `NUM_TO_SKIP` and `NUM_TO_PROCESS` to produce the working file list.

### 3.3  Parse Template Metadata (per file)

Log the filename being processed. Derive template-level metadata from the **file name** (the portion before `.docx`):

| Metadata field | Source |
|---|---|
| `plsqt_name` | Full filename stem (e.g. `UBM 20 FU_FU E`) |
| `product_line` | First 3 characters of the filename, trimmed. `ECM` -> ECM AP product line, `UBM` -> UBM, `KD ` -> KD. Resolved to `product_line.product_line_id` by matching against `product_line.product_line_abbr` (char(3)). |
| `product_cat` | Derived via FK: `product_line.product_cat_id`. |
| `country_id` | From cached lookup (S3.1). |
| `currency_id` | From cached lookup (S3.1). |

If the filename prefix does not map to a known product line, log an error and skip the file (or halt, per `CONTINUE_ON_ERRORS`).

### 3.4  Parse Sections (per file)

Every template is composed of an ordered list of sections. The first section is always the **Cover Page** (all content before the first numbered heading). The remaining sections are identified by numbered headings.

#### 3.4.1  Section Heading Recognition

The parser walks the `.docx` body in document order, examining **both** standalone paragraphs **and** text within table cells. This is required because the sample documents use Word tables for layout, and section headings may appear in either context.

A line is a candidate section heading when **all** of the following are true:

- It matches the pattern: `digit + whitespace/separator (dash or en-dash) + title`.
- It is short (fewer than 80 characters).
- It is either a standalone paragraph or in a single-cell table row (first or last row).

**Table heading detection:** Only table rows with exactly 1 cell are checked for headings. This avoids false positives in multi-column tables (e.g. price summary tables with section references).

**Trailing table headings:** When a heading is found in the **last row** of a multi-row table, it is treated as "trailing" — the table itself belongs to the preceding section's content, and only the heading row starts the new section.

Each section found is logged with its sequence number and heading text.

#### 3.4.2  TOC-Driven Section Validation (new in v2.0)

Instead of hardcoded expected sequences per product line, v2.0 derives expected sections from the document itself:

1. **Extract TOC entries** from the cover page (section 0). The cover page content is scanned for patterns like `3 - Machine Execution` or `3 – Machine Execution`. The regex handles both newline-separated entries and entries concatenated on a single line (common in docx table cell extraction).

2. **Build expected sequence:** `[0] + [section numbers from TOC entries]`.

3. **Compare** actual parsed section numbers against the expected sequence. If they differ, log all TOC entries and all parsed headings, and treat the file as an error.

4. **Fallback:** If no TOC entries are found on the cover page, fall back to a basic count check (minimum 6 sections required).

This approach is self-describing: each template carries its own table of contents, eliminating the need to maintain hardcoded expected-sequence tables.

#### 3.4.3  Section Content Capture

- **Cover Page (seq 0):** All content from the start of the document up to (but not including) the heading for section 1.
- **Intermediate sections:** All content from a section heading up to (but not including) the next section heading.
- **Final section (e.g. Terms of Delivery):** All content from its heading through the end of the document.

Content is stored as **plain text** extracted from the `.docx` paragraphs and tables within the section boundaries. The original `.docx` binary is preserved in `document_blob` for any downstream processing that needs full fidelity.

### 3.5  Section-Type Matching — Longest Common Substring (new in v2.0)

v1 used a 12-character prefix match via SQL. v2.0 replaces this with an in-memory **longest-common-substring (LCS)** algorithm:

1. All section types are pre-fetched once at startup (`fetch_all_section_types()`).
2. For each parsed section heading, the heading text is compared against every `plsqtst_name` using a case-insensitive LCS calculation.
3. The section type with the **longest** common substring wins. Ties are broken by lowest `plsqtst_id`.
4. A **minimum match length of 4** characters is required. If the best LCS is shorter than 4, the heading is treated as unmatched and raises an error.

**Why LCS?** The 12-char prefix match was brittle — headings like "Product Pump FZ 1300" and "Product Pump FZ/FU" share a prefix but are distinct. LCS is more robust against variations in model-specific suffixes and minor wording differences, while still being deterministic and fast for the small set of section types (~20).

**Complexity:** The LCS function uses standard dynamic programming, `O(m * n)` per comparison. Since there are at most ~20 section types and ~10 sections per file, the total cost is negligible.

### 3.6  Store to Database (per file)

All database writes for a single file are wrapped in a **single transaction**. On any failure the transaction is rolled back and the file is treated as an error.

When `NOUPDATE` is `true`, this entire step is skipped.

#### 3.6.1  Duplicate Handling

If a template with the same `plsqt_name` already exists in `plsq_templates`:

1. Record the old `current_blob_id` in `document_blob_history` (entity_type = `'template'`, entity_id = existing `plsqt_id`).
2. Delete all existing `plsqt_sections` rows for that template (the FK has `ON DELETE CASCADE`).
3. Update the `plsq_templates` row with new values.
4. Insert new `plsqt_sections` rows.

If no duplicate exists, insert a new `plsq_templates` row.

#### 3.6.2  `document_blob`

| Column | Value |
|---|---|
| `bytes` | Raw bytes of the original `.docx` file |
| `sha256` | SHA-256 hash of the file bytes |
| `size_bytes` | File size in bytes |
| `content_type` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `original_filename` | Original filename including `.docx` extension |

If a row with the same `sha256` already exists, reuse the existing `blob_id` (do not insert a duplicate).

#### 3.6.3  `plsq_templates`

| Column | Value |
|---|---|
| `country_id` | Looked up from `TEMPLATE_COUNTRY_IN` |
| `currency_id` | Looked up from `TEMPLATE_CURRENCY_IN` |
| `product_cat_id` | Via `product_line.product_cat_id` |
| `product_line_id` | Looked up from filename prefix |
| `current_blob_id` | `blob_id` from S3.6.2 |
| `plsqt_name` | Filename stem |
| `plsqt_section_count` | Number of sections parsed (including cover page) |
| `plsqt_as_of_date` | Current date |
| `plsqt_extrn_file_ref` | Full path to source file |
| `plsqt_active` | `true` |
| `plsqt_status` | `'not started'` |
| `last_update_datetime` | Current timestamp |
| `last_update_user` | `'SQM_loader'` |
| `plsqt_enabled` | `1` |

Returns the generated `plsqt_id`.

#### 3.6.4  `plsqt_sections` (one row per section)

| Column | Value |
|---|---|
| `plsqt_id` | FK to the parent template |
| `section_type_id` | FK to `plsqts_type`, resolved by **LCS match** (S3.5). For the cover page, the heading `"Cover Page"` is matched via LCS like any other heading. |
| `plsqts_seqn` | 0-based sequence (cover page = 0, first numbered section = 1, ...) |
| `plsqts_content` | Extracted plain-text content for this section |
| `plsqts_active` | `true` |
| `plsqts_status` | `'not started'` |
| `last_update_datetime` | Current timestamp |
| `last_update_user` | `'SQM_loader'` |
| `plsqts_enabled` | `1` |

### 3.7  Finalise

1. Log the end-of-run summary (see S5.3).
2. Close the database connection.
3. Close the log file.

---

## 4  Console Output

During processing, write single-character progress indicators to the console **without** a newline:

- **`T`** — starting a new template file.
- **`S`** — each section found within the current template.

Example for a run of 3 files with 9, 9, and 10 sections respectively:

```
TSSSSSSSSTSSSSSSSSSTSSSSSSSSSS
```

After all files are processed, write a newline, then the summary.

When `SILENT` is `false`, all log messages are also echoed to the console.

---

## 5  Logging

### 5.1  Log File Name

```
SQM_{LOG_FILENAME_SLUG}_v{VERSION}_{YYMMDD}_{HHMMSS}_log.txt
```

Example: `SQM_load_templates_v21_260206_153012_log.txt`

### 5.2  Log Line Format

```
SQMLoad|{YYMMDD}_{HHMMSS}|{message}
```

Timestamps use 24-hour time. Each line is terminated with the platform line ending.

### 5.3  Required Log Messages

| Event | Message content |
|---|---|
| Start | Program version, input folder, source country and currency, start timestamp |
| NOUPDATE mode | Note that no database writes will occur (when enabled) |
| File discovery | Count of `.docx` files found (or "no files found") |
| Skip notice | Number of files skipped (when `NUM_TO_SKIP` > 0) |
| Each file opened | `Reading file "{path}"` (includes full filename) |
| Each section found | Section sequence number, matched heading text |
| Section type matched | Blob ID after blob get-or-create |
| Template create/update | Template ID and whether new or updated |
| Old sections deleted | Count of deleted old sections (on update) |
| Old blob archived | Old blob ID (when blob changes on update) |
| Section sequence error | TOC entries, parsed headings, and the mismatch point |
| File-level error | Error description, ordinal file number in the run, filename |
| End | Start timestamp, end timestamp, elapsed time, files read, files stored, sections stored, files skipped, files failed |

### 5.4  Error Handling

- All exceptions — including I/O errors, Unicode errors, and database errors — are caught at the per-file level.
- Errors are logged with the ordinal file number and filename.
- On error, the current transaction is rolled back.
- Behaviour after an error is governed by `CONTINUE_ON_ERRORS`.

---

## 6  Module Architecture

v2.0 factors the program into a main script and three library modules under `1_listldr_lib/`. Modules are imported via `importlib` because the directory name starts with a digit (not a valid Python package name).

| Module | File | Responsibility |
|---|---|---|
| Main | `SQM_load_quote_template_docx_file_v2.0.py` | CLI, config, file loop, orchestration |
| Logger | `1_listldr_lib/sqm_logger.py` | Dual-output logging (file + console), progress indicators |
| Database | `1_listldr_lib/sqm_db.py` | All SQL operations, connection/transaction management, LCS matching |
| DOCX Parser | `1_listldr_lib/sqm_docx_parser.py` | Section heading recognition, content extraction, TOC parsing, validation |

### 6.1  Key Classes and Functions

**`sqm_logger.SQMLogger`** — Context manager. Opens log file on creation, provides `log()`, `progress()`, `newline()`, `close()`.

**`sqm_db.DBConfig`** — Dataclass holding connection parameters (host, port, user, password, database).

**`sqm_db.SQMDatabase`** — Context manager. Methods:

| Method | Purpose |
|---|---|
| `lookup_country(abbr)` | Resolve country abbreviation to `country_id` |
| `lookup_currency(symbol)` | Resolve currency symbol to `currency_id` |
| `lookup_product_line(abbr)` | Resolve 3-char product line abbreviation to `(product_line_id, product_cat_id)` |
| `fetch_all_section_types()` | Pre-fetch all `(plsqtst_id, plsqtst_name)` tuples |
| `lookup_section_type_by_lcs(heading, types, min=4)` | **New in v2.0.** Match heading to best section type via LCS |
| `lookup_section_type(heading)` | *Deprecated.* 12-char prefix match (v1 only) |
| `get_or_create_blob(bytes, filename)` | Deduplicate by SHA-256, return `blob_id` |
| `archive_blob(entity_type, entity_id, blob_id)` | Write to `document_blob_history` |
| `get_template_by_name(name)` | Check for existing template |
| `delete_template_sections(plsqt_id)` | Delete old sections before re-insert |
| `update_template(...)` | Update existing `plsq_templates` row |
| `insert_template(...)` | Insert new `plsq_templates` row |
| `insert_section(...)` | Insert one `plsqt_sections` row |
| `commit()` / `rollback()` | Transaction control |

**`sqm_docx_parser.Section`** — Dataclass with `sequence` (int), `heading` (str), `content` (str).

**`sqm_docx_parser` functions:**

| Function | Purpose |
|---|---|
| `parse_docx_sections(file_path)` | Walk `.docx` body, return list of `Section` objects |
| `extract_toc_entries(sections)` | **New in v2.0.** Parse TOC from cover page content |
| `validate_section_sequence(sections, product_line_abbr)` | **Changed in v2.0.** Uses TOC instead of hardcoded sequences |
| `FIRST_SECTION_HEADING` | Constant: `"Principal Characteristics"` |

---

## 7  Key Database Relationships

Derived from the `listmgr1` DDL for reference:

```
plsqts_type                     (lookup -- section type definitions)
    ^ section_type_id
plsqt_sections                  (child -- one per section)
    ^ plsqt_id
plsq_templates                  (parent -- one per file)
    |-- country_id       -> country
    |-- currency_id      -> currency
    |-- product_cat_id   -> product_cat
    |-- product_line_id  -> product_line
    +-- current_blob_id  -> document_blob

document_blob_history           (audit trail for blob replacements)
    +-- blob_id          -> document_blob
```

Reference queries:

```sql
-- Country
SELECT country_id FROM country
 WHERE country_abbr = :country_abbr AND country_enabled = 1;

-- Currency
SELECT currency_id FROM currency
 WHERE currency_symbol = :currency_symbol AND currency_enabled = 1;

-- Product line (per file, using first 3 chars of filename)
SELECT product_line_id, product_cat_id FROM product_line
 WHERE product_line_abbr = :abbr AND product_line_enabled = 1;

-- Section types: all rows, pre-fetched once (v2.0)
SELECT plsqtst_id, plsqtst_name FROM plsqts_type ORDER BY plsqtst_id ASC;

-- LCS matching is done in Python, not SQL (v2.0)
```

---

## 8  Dependencies

| Package | Version | Purpose |
|---|---|---|
| `python-docx` | >= 0.8 | Parse `.docx` files |
| `psycopg2` | >= 2.9 | PostgreSQL driver |
| Python | >= 3.10 | Type hints (`X | Y`, `list[T]`) |
