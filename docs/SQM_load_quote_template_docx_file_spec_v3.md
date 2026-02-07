# SQM Load Quote Template — Program Specification

**Program:** `SQM_load_quote_template_docx_file.py`
**Version:** 0.01
**Database:** `listmgr1` (PostgreSQL 17, public schema)
**Spec revision:** v3 — 2025-02-06

---

## 1  Purpose

Read one or more WAB sales-quote template files (`.docx`) from a local directory, parse each file into its constituent sections, and store the results in the `listmgr1` database. The input files are **Swiss (CHE) originals** in CHF. A separate, future program will generate converted (e.g. USA/USD) templates.

| Target table | One row per… |
|---|---|
| `plsq_templates` | template file |
| `plsqt_sections` | section within a template |
| `document_blob` | original `.docx` binary |
| `document_blob_history` | (written when an existing blob is replaced) |

Section types are resolved against the existing `plsqts_type` lookup table; they are **not** created by this program.

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
| `NUM_TO_SKIP` | int ≥ 0 | `0` | Number of files to skip (alphabetical order) before processing begins. |
| `NUM_TO_PROCESS` | int ≥ 0 | `0` | Maximum files to process. `0` = no limit (process all). |
| `NOUPDATE` | bool | `false` | When `true`, all database writes are suppressed; parsing and logging still occur (dry-run mode). |
| `CONTINUE_ON_ERRORS` | bool | `true` | When `true`, a file-level error is logged and the program advances to the next file. When `false`, the program halts on the first error. |
| `SILENT` | bool | `false` | When `true`, only start/stop messages and progress indicators (`T`, `S`) are written to the console; all other detail goes to the log file only. |

### 2.2  Database Connection

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
Initialise  →  Discover files  →  For each file:  →  Finalise
                                    Parse metadata
                                    Parse sections
                                    Validate section sequence
                                    Store to DB (unless NOUPDATE)
```

### 3.1  Initialise

1. Read INI file; apply command-line overrides.
2. Open the log file (see §5).
3. Log the start-of-run message including program version, start timestamp, input folder, and source country/currency.
4. Connect to the database.
5. Look up and cache the `country_id` and `currency_id` for the configured source country and currency.

### 3.2  Discover Files

1. List all `.docx` files in `TEMPLATE_INPUT_FOLDER`.
2. Sort alphabetically (case-insensitive).
3. If no files are found, log the fact and exit.
4. Log the count of files found.
5. Apply `NUM_TO_SKIP` and `NUM_TO_PROCESS` to produce the working file list.

### 3.3  Parse Template Metadata (per file)

Log the filename being processed. Derive template-level metadata from the **file name** (the portion before `.docx`):

| Metadata field | Source |
|---|---|
| `plsqt_name` | Full filename stem (e.g. `UBM 20 FU_FU E`) |
| `product_line` | First 3 characters of the filename, trimmed. `ECM` → ECM AP product line, `UBM` → UBM, `KD ` → KD. Resolved to `product_line.product_line_id` by matching against `product_line.product_line_abbr` (char(3)). The 3-character code uniquely identifies the product line even though it may not match the full product-line name. |
| `product_cat` | Derived via FK: `product_line.product_cat_id`. |
| `country_id` | From cached lookup (§3.1). |
| `currency_id` | From cached lookup (§3.1). |

If the filename prefix does not map to a known product line, log an error and skip the file (or halt, per `CONTINUE_ON_ERRORS`).

### 3.4  Parse Sections (per file)

Every template is composed of an ordered list of sections. The first section is always the **Cover Page** (all content before the first numbered heading). The remaining sections are identified by numbered headings.

#### 3.4.1  Section Heading Recognition

The parser walks the `.docx` body in document order, examining **both** standalone paragraphs **and** text within table cells. This is required because the sample documents use Word tables for layout, and section headings may appear in either context.

A line is a candidate section heading when **all** of the following are true:

- It begins with a single digit (1–9), followed by whitespace or a separator (dash, en-dash).
- It is short (fewer than 80 characters).
- It is a standalone line — either a Word `Heading` style, or the sole text of a short paragraph or table cell (not embedded in a body paragraph).

The heading text **after** the leading digit and separator is matched against `plsqts_type.plsqtst_name` using a **case-insensitive prefix match on the first 12 characters**. The **first** matching row (ordered by `plsqtst_id ASC`) is accepted. This prefix-match approach is intentional: multiple section types may share a 12-character prefix (e.g. several "Terms of Delivery" variants). A human will correct the type assignment later if needed.

Each section found is logged with its sequence number and matched section-type name.

#### 3.4.2  Expected Section Sequences by Product Line (Swiss / CHE Templates)

The program validates that sections appear in the expected order. The expected sequences are:

| Seq | CH-Mill-ECM | CH-Mill-UBM | CH-Mill-KD |
|--:|---|---|---|
| 0 | Cover Page | Cover Page | Cover Page |
| 1 | Principal Characteristics | Principal Characteristics | Principal Characteristics |
| 2 | General Technical Data | General Technical Data | General Technical Data |
| 3 | Machine Execution | Machine Execution | Basic Execution |
| 4 | Product Pump … | Product Pump … | Machine Equipment |
| 5 | Motor Starter Cabinet … | Motor Starter Cabinet … | Product Pump … |
| 6 | Price Summary | Price Summary | Motor Starter Cabinet … |
| 7 | Options and Accessories | Options and Accessories | Price Summary |
| 8 | Terms of Delivery | Terms of Delivery | Options and Accessories |
| 9 | — | — | Terms of Delivery |

*Ellipsis (…) indicates that the full heading includes a model-specific suffix (e.g. "Product Pump FZ 1300", "Motor Starter Cabinet MSC-FC/FC"). Only the first 12 characters are used for matching, so these suffixes do not affect recognition.*

ECM and UBM templates have 8 numbered sections (+ cover page = 9 total). KD templates have 9 numbered sections (+ cover page = 10 total).

#### 3.4.3  Section Content Capture

- **Cover Page (seq 0):** All content from the start of the document up to (but not including) the heading for section 1.
- **Intermediate sections:** All content from a section heading up to (but not including) the next section heading.
- **Terms of Delivery (final section):** All content from its heading through the end of the document.

Content is stored as **plain text** extracted from the `.docx` paragraphs and tables within the section boundaries. The original `.docx` binary is preserved in `document_blob` for any downstream processing that needs full fidelity. A future enhancement may store richer representations (e.g. markdown) in `plsqts_content`.

#### 3.4.4  Validation

- All expected sections for the product line must be found, in the order defined in §3.4.2.
- If a section is missing or out of order, log every heading found so far and the point where the sequence broke. Treat the file as an error.
- A template must contain at least 5 section headings (not counting the cover page) to be considered valid.

### 3.5  Store to Database (per file)

All database writes for a single file are wrapped in a **single transaction**. On any failure the transaction is rolled back and the file is treated as an error.

When `NOUPDATE` is `true`, this entire step is skipped.

#### 3.5.1  Duplicate Handling

If a template with the same `plsqt_name` already exists in `plsq_templates`:

1. Record the old `current_blob_id` in `document_blob_history` (entity_type = `'template'`, entity_id = existing `plsqt_id`).
2. Delete all existing `plsqt_sections` rows for that template (the FK has `ON DELETE CASCADE`).
3. Update the `plsq_templates` row with new values.
4. Insert new `plsqt_sections` rows.

If no duplicate exists, insert a new `plsq_templates` row.

#### 3.5.2  `document_blob`

| Column | Value |
|---|---|
| `bytes` | Raw bytes of the original `.docx` file |
| `sha256` | SHA-256 hash of the file bytes |
| `size_bytes` | File size in bytes |
| `content_type` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `original_filename` | Original filename including `.docx` extension |

If a row with the same `sha256` already exists, reuse the existing `blob_id` (do not insert a duplicate).

#### 3.5.3  `plsq_templates`

| Column | Value |
|---|---|
| `country_id` | Looked up from `TEMPLATE_COUNTRY_IN` |
| `currency_id` | Looked up from `TEMPLATE_CURRENCY_IN` |
| `product_cat_id` | Via `product_line.product_cat_id` |
| `product_line_id` | Looked up from filename prefix |
| `current_blob_id` | `blob_id` from §3.5.2 |
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

#### 3.5.4  `plsqt_sections` (one row per section)

| Column | Value |
|---|---|
| `plsqt_id` | FK to the parent template |
| `section_type_id` | FK to `plsqts_type`, resolved by 12-char prefix match (§3.4.1). For the cover page, match against `'Cover Page'` — the first matching row by `plsqtst_id ASC` is used. |
| `plsqts_seqn` | 0-based sequence (cover page = 0, first numbered section = 1, …) |
| `plsqts_content` | Extracted plain-text content for this section |
| `plsqts_active` | `true` |
| `plsqts_status` | `'not started'` |
| `last_update_datetime` | Current timestamp |
| `last_update_user` | `'SQM_loader'` |
| `plsqts_enabled` | `1` |

### 3.6  Finalise

1. Log the end-of-run summary (see §5.3).
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

Example: `SQM_load_templates_v0.01_260131_230415_log.txt`

### 5.2  Log Line Format

```
SQMLoad|{YYMMDD}_{HHMMSS}|{message}
```

Timestamps use 24-hour time. Each line is terminated with the platform line ending.

### 5.3  Required Log Messages

| Event | Message content |
|---|---|
| Start | Program version, input folder, source country and currency, start timestamp |
| File discovery | Count of `.docx` files found (or "no files found") |
| Each file opened | `Reading file "{path}"` (includes full filename) |
| Each section found | Section sequence number, matched section-type name |
| Section sequence error | All headings found so far and the point where sequence broke |
| File-level error | Error description, ordinal file number in the run, filename |
| End | Start timestamp, end timestamp, files read, files stored successfully, total sections stored, files skipped at start, files failed |

### 5.4  Error Handling

- All exceptions — including I/O errors, Unicode errors, and database errors — are caught at the per-file level.
- Errors are logged with the ordinal file number and filename.
- Behaviour after an error is governed by `CONTINUE_ON_ERRORS`.

---

## 6  Key Database Relationships

Derived from the `listmgr1` DDL for reference:

```
plsqts_type                     (lookup — section type definitions)
    ↑ section_type_id
plsqt_sections                  (child — one per section)
    ↑ plsqt_id
plsq_templates                  (parent — one per file)
    ├── country_id       → country
    ├── currency_id      → currency
    ├── product_cat_id   → product_cat
    ├── product_line_id  → product_line
    └── current_blob_id  → document_blob

document_blob_history           (audit trail for blob replacements)
    └── blob_id          → document_blob
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

-- Section type (per heading, first match wins)
SELECT plsqtst_id FROM plsqts_type
 WHERE LOWER(LEFT(plsqtst_name, 12)) = LOWER(LEFT(:heading_text, 12))
 ORDER BY plsqtst_id ASC
 LIMIT 1;
```
