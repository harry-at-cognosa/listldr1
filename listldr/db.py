"""
SQM Database Module

Database operations for the SQM template loader using psycopg2.
Handles lookups, CRUD operations, and transaction management.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from listldr.text_utils import longest_common_substring


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass
class DBConfig:
    """Database connection configuration."""
    host: str
    port: int
    user: str
    password: str
    database: str


class SQMDatabase:
    """Database manager for SQM template loading."""

    def __init__(self, config: DBConfig | None = None, conn=None):
        self.config = config
        self.conn = conn

    def connect(self) -> None:
        """Open database connection."""
        if self.conn is not None:
            return  # already have an injected connection
        if self.config is None:
            raise ValueError("No config or connection provided")
        self.conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
        )
        # Disable autocommit for transaction control
        self.conn.autocommit = False

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def commit(self) -> None:
        """Commit the current transaction."""
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self.conn:
            self.conn.rollback()

    # -------------------------------------------------------------------------
    # Lookup Methods
    # -------------------------------------------------------------------------

    def lookup_country(self, country_abbr: str) -> Optional[int]:
        """
        Look up country_id by country_abbr.
        Returns None if not found or not enabled.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT country_id FROM country
                WHERE country_abbr = %s AND country_enabled = 1
                """,
                (country_abbr,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def lookup_currency(self, currency_symbol: str) -> Optional[int]:
        """
        Look up currency_id by currency_symbol.
        Returns None if not found or not enabled.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT currency_id FROM currency
                WHERE currency_symbol = %s AND currency_enabled = 1
                """,
                (currency_symbol,)
            )
            row = cur.fetchone()
            return row[0] if row else None

    def lookup_product_line(self, abbr: str) -> Optional[tuple[int, int]]:
        """
        Look up product_line by 3-char abbreviation.
        Returns (product_line_id, product_cat_id) or None if not found.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT product_line_id, product_cat_id FROM product_line
                WHERE product_line_abbr = %s AND product_line_enabled = 1
                """,
                (abbr,)
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None

    def fetch_all_section_types(self) -> list[tuple[int, str]]:
        """
        Fetch all section types from plsqts_type, ordered by id.
        Returns list of (plsqtst_id, plsqtst_name). Intended to be called
        once and cached for reuse across all files.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT plsqtst_id, plsqtst_name FROM plsqts_type ORDER BY plsqtst_id ASC"
            )
            return cur.fetchall()

    def lookup_section_type_by_lcs(
        self,
        heading_text: str,
        section_types: list[tuple[int, str]],
        min_match_length: int = 4,
    ) -> Optional[int]:
        """
        Match heading_text to a section type using longest-common-substring.

        Iterates over pre-fetched section_types, computes LCS against heading_text.
        Returns plsqtst_id of the best match (longest LCS); ties broken by lowest id.
        Returns None if the best LCS length < min_match_length.
        """
        best_id = None
        best_len = 0

        for type_id, type_name in section_types:
            lcs_len = longest_common_substring(heading_text, type_name)
            if lcs_len > best_len:
                best_len = lcs_len
                best_id = type_id

        if best_len < min_match_length:
            return None
        return best_id

    # -------------------------------------------------------------------------
    # Blob Operations
    # -------------------------------------------------------------------------

    def get_or_create_blob(
        self,
        file_bytes: bytes,
        original_filename: str
    ) -> int:
        """
        Get existing blob by SHA256 or create new one.
        Returns blob_id.
        """
        sha256_hash = hashlib.sha256(file_bytes).digest()
        size_bytes = len(file_bytes)

        with self.conn.cursor() as cur:
            # Check if blob already exists
            cur.execute(
                "SELECT blob_id FROM document_blob WHERE sha256 = %s",
                (sha256_hash,)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            # Insert new blob
            cur.execute(
                """
                INSERT INTO document_blob (bytes, sha256, size_bytes, content_type, original_filename)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING blob_id
                """,
                (
                    psycopg2.Binary(file_bytes),
                    psycopg2.Binary(sha256_hash),
                    size_bytes,
                    DOCX_CONTENT_TYPE,
                    original_filename,
                )
            )
            return cur.fetchone()[0]

    def archive_blob(
        self,
        entity_type: str,
        entity_id: int,
        blob_id: int,
        replaced_by: str = "SQM_loader"
    ) -> None:
        """Record old blob in history before replacement."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_blob_history (entity_type, entity_id, blob_id, replaced_by)
                VALUES (%s, %s, %s, %s)
                """,
                (entity_type, entity_id, blob_id, replaced_by)
            )

    # -------------------------------------------------------------------------
    # Template Operations
    # -------------------------------------------------------------------------

    def get_template_by_name(self, plsqt_name: str) -> Optional[dict]:
        """
        Get existing template by name.
        Returns dict with plsqt_id and current_blob_id, or None.
        """
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT plsqt_id, current_blob_id FROM plsq_templates
                WHERE plsqt_name = %s
                """,
                (plsqt_name,)
            )
            return cur.fetchone()

    def delete_template_sections(self, plsqt_id: int) -> int:
        """Delete all sections for a template. Returns count deleted."""
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM plsqt_sections WHERE plsqt_id = %s",
                (plsqt_id,)
            )
            return cur.rowcount

    def update_template(
        self,
        plsqt_id: int,
        country_id: int,
        currency_id: int,
        product_cat_id: int,
        product_line_id: int,
        blob_id: int,
        section_count: int,
        file_path: str,
        update_user: str = "SQM_loader",
    ) -> None:
        """Update an existing template row."""
        now = datetime.now()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE plsq_templates SET
                    country_id = %s,
                    currency_id = %s,
                    product_cat_id = %s,
                    product_line_id = %s,
                    current_blob_id = %s,
                    plsqt_section_count = %s,
                    plsqt_as_of_date = %s,
                    plsqt_extrn_file_ref = %s,
                    plsqt_active = true,
                    plsqt_status = 'not started',
                    last_update_datetime = %s,
                    last_update_user = %s,
                    plsqt_enabled = 1
                WHERE plsqt_id = %s
                """,
                (
                    country_id,
                    currency_id,
                    product_cat_id,
                    product_line_id,
                    blob_id,
                    section_count,
                    date.today(),
                    file_path,
                    now,
                    update_user,
                    plsqt_id,
                )
            )

    def insert_template(
        self,
        plsqt_name: str,
        country_id: int,
        currency_id: int,
        product_cat_id: int,
        product_line_id: int,
        blob_id: int,
        section_count: int,
        file_path: str,
        update_user: str = "SQM_loader",
    ) -> int:
        """Insert a new template row. Returns plsqt_id."""
        now = datetime.now()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO plsq_templates (
                    plsqt_name,
                    country_id,
                    currency_id,
                    product_cat_id,
                    product_line_id,
                    current_blob_id,
                    plsqt_section_count,
                    plsqt_as_of_date,
                    plsqt_extrn_file_ref,
                    plsqt_active,
                    plsqt_status,
                    last_update_datetime,
                    last_update_user,
                    plsqt_enabled
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, true, 'not started', %s, %s, 1
                )
                RETURNING plsqt_id
                """,
                (
                    plsqt_name,
                    country_id,
                    currency_id,
                    product_cat_id,
                    product_line_id,
                    blob_id,
                    section_count,
                    date.today(),
                    file_path,
                    now,
                    update_user,
                )
            )
            return cur.fetchone()[0]

    # -------------------------------------------------------------------------
    # Section Operations
    # -------------------------------------------------------------------------

    def insert_section(
        self,
        plsqt_id: int,
        section_type_id: int,
        seqn: int,
        content: str,
        update_user: str = "SQM_loader",
    ) -> int:
        """Insert a section row. Returns plsqts_id."""
        now = datetime.now()
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO plsqt_sections (
                    plsqt_id,
                    section_type_id,
                    plsqts_seqn,
                    plsqts_content,
                    plsqts_active,
                    plsqts_status,
                    last_update_datetime,
                    last_update_user,
                    plsqts_enabled
                ) VALUES (
                    %s, %s, %s, %s, true, 'not started', %s, %s, 1
                )
                RETURNING plsqts_id
                """,
                (plsqt_id, section_type_id, seqn, content, now, update_user)
            )
            return cur.fetchone()[0]

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.close()
        return False
