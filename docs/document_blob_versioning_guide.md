# Document Blob Versioning Guide

Answers the question:

please create a markdown document that explains to a programer a) the way 
  that documents associated with a row in the plsq_templates file is       
  associated with a docx file stored in the document_blob table via it's    
  current_blob_id which is an FK to the PK blob_id field in that table.     
  explain also how the document blob history file is used to link to prior  
  versions (if any) of that docx file in the document_blob_history file     
  when a new version of the plsq_template record's document is updated. 

How `plsq_templates` rows link to their `.docx` files and how prior document versions are tracked.

---

## 1. Overview

Three tables work together to store template documents and maintain version history:

| Table | Purpose |
|---|---|
| `plsq_templates` | Template metadata; points to the **current** `.docx` via `current_blob_id` |
| `document_blob` | Immutable binary storage of `.docx` files, deduplicated by SHA-256 |
| `document_blob_history` | Audit trail recording which blobs were **replaced** and when |

---

## 2. Table Schemas (Relevant Columns)

### `document_blob`

```sql
CREATE TABLE document_blob (
    blob_id       bigint    NOT NULL PRIMARY KEY,   -- auto-increment
    bytes         bytea     NOT NULL,               -- raw .docx binary content
    sha256        bytea     NOT NULL,               -- SHA-256 hash (exactly 32 bytes)
    size_bytes    integer   NOT NULL,               -- file size in bytes
    content_type  text      NOT NULL,               -- MIME type
    original_filename text,                         -- e.g. "ECM AP 10 CHE.docx"
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT document_blob_sha256_len CHECK (octet_length(sha256) = 32),
    CONSTRAINT document_blob_size_chk   CHECK (size_bytes = octet_length(bytes))
);

-- Prevents storing the same file twice
ALTER TABLE document_blob
    ADD CONSTRAINT document_blob_sha256_unique UNIQUE (sha256);
```

Each row is **immutable** -- once a blob is created it is never modified, only read or eventually archived.

### `plsq_templates`

```sql
CREATE TABLE plsq_templates (
    plsqt_id          integer       NOT NULL PRIMARY KEY,  -- auto-increment
    plsqt_name        text,                                -- template name (file stem)
    current_blob_id   bigint,                              -- FK to document_blob
    -- ... other metadata columns (country_id, currency_id, etc.)

    CONSTRAINT plsq_templates_current_blob_id_fkey
        FOREIGN KEY (current_blob_id) REFERENCES document_blob(blob_id)
);

CREATE INDEX idx_templates_blob ON plsq_templates (current_blob_id);
```

`current_blob_id` is the single link from a template to its **current** `.docx` file.

### `document_blob_history`

```sql
CREATE TABLE document_blob_history (
    history_id   bigint       NOT NULL PRIMARY KEY,  -- auto-increment
    entity_type  text         NOT NULL,              -- 'template' or 'quote'
    entity_id    integer      NOT NULL,              -- plsqt_id (when entity_type = 'template')
    blob_id      bigint       NOT NULL,              -- the OLD blob that was replaced
    replaced_at  timestamptz  NOT NULL DEFAULT now(), -- when the replacement happened
    replaced_by  varchar(50),                         -- user or process name

    CONSTRAINT blob_history_entity_type_chk
        CHECK (entity_type IN ('template', 'quote')),

    CONSTRAINT document_blob_history_blob_id_fkey
        FOREIGN KEY (blob_id) REFERENCES document_blob(blob_id)
);

CREATE INDEX idx_blob_history_entity ON document_blob_history (entity_type, entity_id);
CREATE INDEX idx_blob_history_blob   ON document_blob_history (blob_id);
```

Each row records a **single replacement event**: "entity X used to point to blob Y, and that link was replaced at time Z."

---

## 3. Relationship Diagram

```
plsq_templates                 document_blob
+-----------------+            +-------------------+
| plsqt_id  (PK)  |            | blob_id  (PK)     |
| plsqt_name      |            | bytes             |
| current_blob_id |---FK------>| sha256  (UNIQUE)  |
| ...             |            | size_bytes        |
+-----------------+            | content_type      |
                               | original_filename |
                               | created_at        |
                               +-------------------+
                                       ^
                                       | FK (blob_id)
                                       |
                          document_blob_history
                          +--------------------+
                          | history_id  (PK)   |
                          | entity_type        |  = 'template'
                          | entity_id          |  = plsqt_id
                          | blob_id            |---> points to the OLD blob
                          | replaced_at        |
                          | replaced_by        |
                          +--------------------+
```

- `plsq_templates.current_blob_id` always points to the **current** document blob.
- `document_blob_history` rows point to **previous** blobs that were replaced.
- There is no direct FK from `document_blob_history.entity_id` to `plsq_templates.plsqt_id`; the link is logical, identified by `entity_type = 'template'` + `entity_id`.

---

## 4. How a Template Links to Its Document

A template row's `.docx` file is retrieved by joining on `current_blob_id`:

```sql
SELECT
    t.plsqt_id,
    t.plsqt_name,
    b.blob_id,
    b.original_filename,
    b.size_bytes,
    b.created_at
FROM plsq_templates t
JOIN document_blob  b ON b.blob_id = t.current_blob_id
WHERE t.plsqt_name = 'ECM AP 10 CHE';
```

To retrieve the actual binary content (e.g. for download), select `b.bytes`.

If `current_blob_id IS NULL`, the template has no document stored yet.

---

## 5. SHA-256 Deduplication

Before inserting a new blob, the system computes a SHA-256 hash of the file bytes and checks for an existing match. This is handled by `sqm_db.SQMDatabase.get_or_create_blob()` (`1_listldr_lib/sqm_db.py`, line 205):

```python
def get_or_create_blob(self, file_bytes: bytes, original_filename: str) -> int:
    sha256_hash = hashlib.sha256(file_bytes).digest()

    # Check if blob already exists
    cur.execute("SELECT blob_id FROM document_blob WHERE sha256 = %s", (sha256_hash,))
    row = cur.fetchone()
    if row:
        return row[0]          # reuse existing blob_id

    # Insert new blob
    cur.execute(
        "INSERT INTO document_blob (bytes, sha256, size_bytes, content_type, original_filename) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING blob_id",
        (file_bytes, sha256_hash, size_bytes, DOCX_CONTENT_TYPE, original_filename)
    )
    return cur.fetchone()[0]   # return newly generated blob_id
```

This means:
- If you upload the **exact same file** twice, only one `document_blob` row is stored.
- Multiple templates can share the same `blob_id` if their files are byte-identical.

---

## 6. Document Update & Version History Flow

When a new version of a template's `.docx` is loaded (see `SQM_load_quote_template_docx_file_v2.0.py`, lines 217-251), the following steps execute **within a single database transaction**:

### Step 1 -- Create or find the new blob

```python
file_bytes = file_path.read_bytes()
blob_id = db.get_or_create_blob(file_bytes, filename)
```

The new file's SHA-256 is computed. If an identical blob already exists, its `blob_id` is reused; otherwise a new row is inserted into `document_blob`.

### Step 2 -- Look up the existing template

```python
existing = db.get_template_by_name(stem)
# Returns: { 'plsqt_id': 42, 'current_blob_id': 7 }  (or None)
```

### Step 3 -- Archive the old blob (if different)

```python
if old_blob_id and old_blob_id != blob_id:
    db.archive_blob('template', plsqt_id, old_blob_id)
```

This inserts a row into `document_blob_history`:

| Column | Value |
|---|---|
| `entity_type` | `'template'` |
| `entity_id` | the template's `plsqt_id` |
| `blob_id` | the **old** `current_blob_id` being replaced |
| `replaced_at` | `now()` |
| `replaced_by` | `'SQM_loader'` |

The old blob row in `document_blob` is **not deleted** -- it remains available for historical retrieval.

If the new file is byte-identical to the old file (same SHA-256 = same `blob_id`), no history row is created because nothing actually changed.

### Step 4 -- Update the template's current blob pointer

```python
db.update_template(plsqt_id=plsqt_id, ..., blob_id=blob_id, ...)
```

This runs:

```sql
UPDATE plsq_templates
SET current_blob_id = <new_blob_id>,
    last_update_datetime = now(),
    last_update_user = 'SQM_loader',
    ...
WHERE plsqt_id = <plsqt_id>;
```

### Step 5 -- Commit

```python
db.commit()
```

All changes (blob insert, history insert, template update, section deletes/inserts) are committed atomically. On error, the entire transaction is rolled back.

### Summary Diagram

```
BEFORE UPDATE:
  plsq_templates (plsqt_id=42)  --current_blob_id-->  document_blob (blob_id=7)

AFTER UPDATE:
  plsq_templates (plsqt_id=42)  --current_blob_id-->  document_blob (blob_id=15)

  document_blob_history:
    entity_type='template', entity_id=42, blob_id=7, replaced_at='2025-06-15 ...'
                                                 |
                                                 v
                                          document_blob (blob_id=7)  [still exists]
```

---

## 7. Querying Version History

To retrieve all prior document versions for a specific template, ordered most recent first:

```sql
SELECT
    h.history_id,
    h.blob_id        AS old_blob_id,
    h.replaced_at,
    h.replaced_by,
    b.original_filename,
    b.size_bytes,
    b.created_at      AS blob_created_at
FROM document_blob_history h
JOIN document_blob b ON b.blob_id = h.blob_id
WHERE h.entity_type = 'template'
  AND h.entity_id   = 42          -- plsqt_id
ORDER BY h.replaced_at DESC;
```

To get the **complete version timeline** (current + all prior):

```sql
-- Current version
SELECT
    'current' AS version_status,
    b.blob_id,
    b.original_filename,
    b.size_bytes,
    b.created_at,
    NULL AS replaced_at
FROM plsq_templates t
JOIN document_blob  b ON b.blob_id = t.current_blob_id
WHERE t.plsqt_id = 42

UNION ALL

-- Prior versions
SELECT
    'replaced' AS version_status,
    b.blob_id,
    b.original_filename,
    b.size_bytes,
    b.created_at,
    h.replaced_at
FROM document_blob_history h
JOIN document_blob b ON b.blob_id = h.blob_id
WHERE h.entity_type = 'template'
  AND h.entity_id   = 42
ORDER BY replaced_at DESC NULLS FIRST;
```

---

## 8. Source File References

| File | What to look at |
|---|---|
| `docs/listmgr1_db_schema.sql` | DDL for all three tables, constraints, indexes, and FK definitions |
| `1_listldr_lib/sqm_db.py` | `get_or_create_blob()` (line 205), `archive_blob()` (line 244), `get_template_by_name()` (line 265), `update_template()` (line 289) |
| `SQM_load_quote_template_docx_file_v2.0.py` | Complete update orchestration flow (lines 217-251) |
