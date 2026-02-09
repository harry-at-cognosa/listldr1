"""
SQM Template Loader Service Layer

Shared core logic for loading a .docx template into the database.
Called by both the batch CLI and the FastAPI endpoint.
"""

from io import BytesIO
from pathlib import Path

from listldr.db import SQMDatabase
from listldr.models import TemplateLoadResult, SectionInfo
from listldr.parser import parse_docx_sections, validate_section_sequence


def load_template(
    file_bytes: bytes,
    filename: str,
    db: SQMDatabase,
    country_id: int,
    currency_id: int,
    section_types: list[tuple[int, str]],
    *,
    product_line_override: str | None = None,
    update_user: str = "SQM_loader",
    dry_run: bool = False,
    file_ref: str | None = None,
) -> TemplateLoadResult:
    """
    Parse a .docx template and load it into the database.

    Args:
        file_bytes: Raw bytes of the .docx file.
        filename: Original filename (e.g. "ECM AP 10 CHE.docx").
        db: An SQMDatabase instance with an open connection.
        country_id: Resolved country_id.
        currency_id: Resolved currency_id.
        section_types: Pre-fetched list of (plsqtst_id, plsqtst_name).
        product_line_override: 3-char product line; if None, parsed from filename.
        update_user: Audit trail user name.
        dry_run: If True, parse and validate but skip database writes.
        file_ref: External file reference stored on the template row.

    Returns:
        TemplateLoadResult with details of the loaded template.

    Raises:
        ValueError: On validation failures (bad filename, unknown product line,
                     section sequence mismatch, unmatched section type).
    """
    stem = Path(filename).stem

    # Resolve product line
    product_line_abbr = product_line_override or (stem[:3] if len(stem) >= 3 else None)
    if not product_line_abbr or len(product_line_abbr) < 3:
        raise ValueError(f"Filename too short to extract product line: {stem}")

    pl_info = db.lookup_product_line(product_line_abbr)
    if not pl_info:
        raise ValueError(f"Unknown product line abbreviation: '{product_line_abbr}'")
    product_line_id, product_cat_id = pl_info

    # Parse sections from document bytes
    sections = parse_docx_sections(BytesIO(file_bytes))

    # Validate section sequence against TOC
    valid, error_msg = validate_section_sequence(sections, product_line_abbr)
    if not valid:
        raise ValueError(f"Section sequence validation failed: {error_msg}")

    # Match each section to a section type
    section_infos: list[SectionInfo] = []
    for sec in sections:
        section_type_id = db.lookup_section_type_by_lcs(sec.heading, section_types)
        if section_type_id is None:
            raise ValueError(f"No section type found for heading: '{sec.heading}'")
        section_infos.append(SectionInfo(
            sequence=sec.sequence,
            heading=sec.heading,
            section_type_id=section_type_id,
        ))

    if dry_run:
        return TemplateLoadResult(
            plsqt_id=0,
            template_name=stem,
            product_line_abbr=product_line_abbr,
            section_count=len(sections),
            is_new=True,
            blob_id=0,
            sections=section_infos,
        )

    # Store blob
    blob_id = db.get_or_create_blob(file_bytes, filename)
    file_ref = file_ref or filename

    # Check for existing template
    existing = db.get_template_by_name(stem)

    if existing:
        plsqt_id = existing['plsqt_id']
        old_blob_id = existing['current_blob_id']
        is_new = False

        # Archive old blob if different
        if old_blob_id and old_blob_id != blob_id:
            db.archive_blob('template', plsqt_id, old_blob_id, replaced_by=update_user)

        # Delete old sections and update template
        db.delete_template_sections(plsqt_id)
        db.update_template(
            plsqt_id=plsqt_id,
            country_id=country_id,
            currency_id=currency_id,
            product_cat_id=product_cat_id,
            product_line_id=product_line_id,
            blob_id=blob_id,
            section_count=len(sections),
            file_path=file_ref,
            update_user=update_user,
        )
    else:
        is_new = True
        plsqt_id = db.insert_template(
            plsqt_name=stem,
            country_id=country_id,
            currency_id=currency_id,
            product_cat_id=product_cat_id,
            product_line_id=product_line_id,
            blob_id=blob_id,
            section_count=len(sections),
            file_path=file_ref,
            update_user=update_user,
        )

    # Insert sections
    for sec, info in zip(sections, section_infos):
        db.insert_section(
            plsqt_id=plsqt_id,
            section_type_id=info.section_type_id,
            seqn=sec.sequence,
            content=sec.content,
            update_user=update_user,
        )

    return TemplateLoadResult(
        plsqt_id=plsqt_id,
        template_name=stem,
        product_line_abbr=product_line_abbr,
        section_count=len(sections),
        is_new=is_new,
        blob_id=blob_id,
        sections=section_infos,
    )
