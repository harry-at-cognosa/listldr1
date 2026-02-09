# Blob Archive/Cleanup Program — Design

## Context

The `document_blob` table grows without limit as templates and quotes are updated — each new version adds a new blob row containing the full `.docx` file bytes. The `document_blob_history` table tracks which blobs were replaced and when (`replaced_at` timestamp), but the old blob data stays forever. This program provides a way to periodically purge old history entries and the orphaned blob data they point to.

## How Blob Storage Works

```
plsq_templates.current_blob_id ──────┐
                                      ├──► document_blob (blob_id, bytes, sha256, size_bytes, ...)
customer_quotes.current_blob_id ──────┘
                                              ▲
document_blob_history (history_id,            │
    entity_type, entity_id, blob_id, ─────────┘
    replaced_at, replaced_by)
```

- **`document_blob`**: One row per unique file. The `bytes` column (`bytea`) holds the full binary content. Rows are deduplicated by SHA256 hash. This table is heavy — each row is the size of the `.docx` file.
- **`document_blob_history`**: One row per replacement event. Very lightweight — just pointers and timestamps, no file data. The `entity_type` column is constrained to `'template'` or `'quote'`.
- When a template or quote is updated with a new file, the old `blob_id` is recorded in history and the entity's `current_blob_id` is updated to point to the new blob.

## Program: `cli/archive_blobs.py`

### CLI Interface

```
python cli/archive_blobs.py YYMMDD [options]

positional:
  cutoff            Cutoff date in YYMMDD format (e.g. 260101 = 2026-01-01).
                    History entries with replaced_at before this date will be removed.

options:
  --entity-type     "template", "quote", or "both" (default: both)
  --ini             DB config file (default: ./conf/listldr_sqt.ini)
  --dry-run         Show what would be deleted, no changes made
```

### Logic (two-step, single transaction)

**Step 1 — Delete old history rows:**

```sql
DELETE FROM document_blob_history
WHERE replaced_at < %(cutoff)s
  AND (%(filter)s = 'both' OR entity_type = %(filter)s)
RETURNING blob_id
```

Collect the set of candidate `blob_id`s from deleted rows.

**Step 2 — Delete orphaned blobs:**

From those candidates, delete only blobs no longer referenced anywhere:

```sql
DELETE FROM document_blob
WHERE blob_id = ANY(%(candidate_ids)s)
  AND blob_id NOT IN (SELECT current_blob_id FROM plsq_templates WHERE current_blob_id IS NOT NULL)
  AND blob_id NOT IN (SELECT current_blob_id FROM customer_quotes WHERE current_blob_id IS NOT NULL)
  AND blob_id NOT IN (SELECT blob_id FROM document_blob_history)
RETURNING blob_id, size_bytes
```

**Order matters:** History rows must be deleted first because `document_blob_history.blob_id` has a foreign key to `document_blob.blob_id`.

**Dry-run mode:** Runs the same queries inside a transaction, then rolls back so counts are accurate without side effects.

### Example Output

```
Blob Archive — cutoff 2026-01-01, entity_type: both
History rows deleted: 12
Orphaned blobs deleted: 8 (3.2 MB freed)

Committed.
```

### Usage Examples

```bash
# Dry-run — see what would be purged before 2026-01-01
python cli/archive_blobs.py 260101 --dry-run

# Templates only
python cli/archive_blobs.py 260101 --entity-type template --dry-run

# Quotes only
python cli/archive_blobs.py 260101 --entity-type quote --dry-run

# Real run (both templates and quotes)
python cli/archive_blobs.py 260101
```

### Safety Notes

- Always run with `--dry-run` first to see what would be affected.
- The orphan check is conservative: a blob is only deleted if it is not referenced by any live template, any live quote, or any remaining history row.
- The entire operation runs in a single transaction — if anything fails, nothing is changed.
