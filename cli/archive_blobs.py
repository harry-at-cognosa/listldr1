#!/usr/bin/env python3
# cli/archive_blobs.py - v1.0 - 2026-02-08
# Purge old document_blob_history entries and orphaned document_blob rows

"""
Blob Archive/Cleanup Program

Deletes document_blob_history rows older than a cutoff date, then removes
any document_blob rows that are no longer referenced by any live entity
or remaining history entry.

Usage:
    python cli/archive_blobs.py YYMMDD [options]

Examples:
    python cli/archive_blobs.py 260101 --dry-run
    python cli/archive_blobs.py 260101 --entity-type template
    python cli/archive_blobs.py 260101

See --help for all options.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path when run as a script (python cli/archive_blobs.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from listldr.config import db_config_from_ini
from listldr.db import SQMDatabase


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Purge old blob history and orphaned blob data."
    )
    parser.add_argument(
        "cutoff",
        help="Cutoff date in YYMMDD format (e.g. 260101 = 2026-01-01). "
             "History entries with replaced_at before this date will be removed."
    )
    parser.add_argument(
        "--entity-type",
        choices=["template", "quote", "both"],
        default="both",
        help="Filter by entity type (default: both)"
    )
    parser.add_argument(
        "--ini",
        default="./conf/listldr_sqt.ini",
        help="Config file path (default: ./conf/listldr_sqt.ini)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without making changes"
    )
    return parser.parse_args()


def parse_cutoff_date(yymmdd: str) -> datetime:
    """Parse YYMMDD string into a datetime."""
    try:
        return datetime.strptime(yymmdd, "%y%m%d")
    except ValueError:
        print(f"Error: Invalid date format '{yymmdd}'. Expected YYMMDD (e.g. 260101).")
        sys.exit(1)


def format_bytes(size_bytes: int) -> str:
    """Format byte count as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    args = parse_args()
    cutoff = parse_cutoff_date(args.cutoff)
    entity_filter = args.entity_type

    db_config = db_config_from_ini(args.ini)

    print(f"Blob Archive — cutoff {cutoff.strftime('%Y-%m-%d')}, entity_type: {entity_filter}")
    if args.dry_run:
        print("DRY RUN — no changes will be made")
    print()

    with SQMDatabase(db_config) as db:
        cur = db.conn.cursor()

        # Step 1: Delete old history rows
        if entity_filter == "both":
            cur.execute(
                """
                DELETE FROM document_blob_history
                WHERE replaced_at < %s
                RETURNING blob_id
                """,
                (cutoff,)
            )
        else:
            cur.execute(
                """
                DELETE FROM document_blob_history
                WHERE replaced_at < %s AND entity_type = %s
                RETURNING blob_id
                """,
                (cutoff, entity_filter)
            )

        deleted_history = cur.fetchall()
        history_count = len(deleted_history)
        candidate_blob_ids = list({row[0] for row in deleted_history})

        print(f"History rows deleted: {history_count}")

        # Step 2: Delete orphaned blobs from the candidate set
        blobs_deleted = 0
        bytes_freed = 0

        if candidate_blob_ids:
            cur.execute(
                """
                DELETE FROM document_blob
                WHERE blob_id = ANY(%s)
                  AND blob_id NOT IN (
                      SELECT current_blob_id FROM plsq_templates
                      WHERE current_blob_id IS NOT NULL
                  )
                  AND blob_id NOT IN (
                      SELECT current_blob_id FROM customer_quotes
                      WHERE current_blob_id IS NOT NULL
                  )
                  AND blob_id NOT IN (
                      SELECT blob_id FROM document_blob_history
                  )
                RETURNING blob_id, size_bytes
                """,
                (candidate_blob_ids,)
            )
            deleted_blobs = cur.fetchall()
            blobs_deleted = len(deleted_blobs)
            bytes_freed = sum(row[1] for row in deleted_blobs)

        print(f"Orphaned blobs deleted: {blobs_deleted} ({format_bytes(bytes_freed)} freed)")

        if args.dry_run:
            db.rollback()
            print("\nRolled back — no changes applied.")
        else:
            db.commit()
            print("\nCommitted.")


if __name__ == "__main__":
    main()
