#!/usr/bin/env python3
# SQM_load_quote_template_docx_file_v2.0.py - v2.1 - 2026-02-06
# SQM Load Quote Template DOCX File — TOC-driven validation, LCS section type matching
# Batch load WAB sales-quote template files (.docx) into the listmgr1 database

"""
SQM Load Quote Template DOCX File

Batch program to load WAB sales-quote template files (.docx) into the listmgr1 database.

Usage:
    python SQM_load_quote_template_docx_file_v2.0.py [options]

See --help for available options.
"""

import argparse
import configparser
import importlib.util
import sys
from datetime import datetime
from pathlib import Path


def _import_from_lib(module_name: str):
    """Import a module from 1_listldr_lib (which has an invalid Python package name)."""
    lib_dir = Path(__file__).parent / "1_listldr_lib"
    module_path = lib_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Import from 1_listldr_lib using importlib (package name starts with digit)
sqm_logger = _import_from_lib("sqm_logger")
sqm_db = _import_from_lib("sqm_db")
sqm_docx_parser = _import_from_lib("sqm_docx_parser")

SQMLogger = sqm_logger.SQMLogger
SQMDatabase = sqm_db.SQMDatabase
DBConfig = sqm_db.DBConfig
parse_docx_sections = sqm_docx_parser.parse_docx_sections
validate_section_sequence = sqm_docx_parser.validate_section_sequence
extract_toc_entries = sqm_docx_parser.extract_toc_entries
FIRST_SECTION_HEADING = sqm_docx_parser.FIRST_SECTION_HEADING
Section = sqm_docx_parser.Section


VERSION = "2.1"


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Load WAB sales-quote template files into listmgr1 database."
    )
    parser.add_argument(
        "--ini",
        default="./conf/listldr_sqt.ini",
        help="Config file path (default: ./conf/listldr_sqt.ini)"
    )
    parser.add_argument(
        "--path-root",
        help="Override PATH_ROOT from config"
    )
    parser.add_argument(
        "--input-folder",
        help="Override TEMPLATE_INPUT_FOLDER from config"
    )
    parser.add_argument(
        "--country",
        help="Override TEMPLATE_COUNTRY_IN from config"
    )
    parser.add_argument(
        "--currency",
        help="Override TEMPLATE_CURRENCY_IN from config"
    )
    parser.add_argument(
        "--skip",
        type=int,
        help="Number of files to skip (NUM_TO_SKIP)"
    )
    parser.add_argument(
        "--process",
        type=int,
        help="Max files to process, 0=all (NUM_TO_PROCESS)"
    )
    parser.add_argument(
        "--noupdate",
        action="store_true",
        help="Dry-run mode: no database writes"
    )
    parser.add_argument(
        "--no-continue",
        action="store_true",
        help="Halt on first error (disable CONTINUE_ON_ERRORS)"
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suppress console detail (progress only)"
    )
    return parser.parse_args()


def load_config(ini_path: str, args: argparse.Namespace) -> dict:
    """Load configuration from INI file with CLI overrides."""
    if not Path(ini_path).exists():
        print(f"Error: Config file not found: {ini_path}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(ini_path)

    # Build config dict with CLI overrides
    cfg = {
        # Paths
        'path_root': args.path_root or config.get('paths', 'PATH_ROOT'),
        'input_folder': args.input_folder or config.get('paths', 'TEMPLATE_INPUT_FOLDER'),
        'log_dir': config.get('paths', 'LOGFILE_DIR_PATH'),

        # Template settings
        'country': args.country or config.get('template', 'TEMPLATE_COUNTRY_IN'),
        'currency': args.currency or config.get('template', 'TEMPLATE_CURRENCY_IN'),
        'log_slug': config.get('template', 'LOG_FILENAME_SLUG'),

        # Processing options
        'skip': args.skip if args.skip is not None else config.getint('processing', 'NUM_TO_SKIP'),
        'process': args.process if args.process is not None else config.getint('processing', 'NUM_TO_PROCESS'),
        'noupdate': args.noupdate or config.getboolean('processing', 'NOUPDATE'),
        'continue_on_errors': not args.no_continue and config.getboolean('processing', 'CONTINUE_ON_ERRORS'),
        'silent': args.silent or config.getboolean('processing', 'SILENT'),

        # Database
        'db_host': config.get('database', 'host'),
        'db_port': config.getint('database', 'port'),
        'db_user': config.get('database', 'user'),
        'db_password': config.get('database', 'password'),
        'db_name': config.get('database', 'database'),
    }

    return cfg


def discover_files(input_dir: Path, skip: int, process: int) -> list[Path]:
    """
    Discover .docx files in input directory.
    Returns sorted list after applying skip/process limits.
    """
    files = sorted(
        [f for f in input_dir.glob("*.docx")
         if not f.name.startswith("~") and not f.stem.isdigit()],
        key=lambda p: p.name.lower()
    )

    # Apply skip
    if skip > 0:
        files = files[skip:]

    # Apply process limit
    if process > 0:
        files = files[:process]

    return files


def process_file(
    file_path: Path,
    db: SQMDatabase,
    country_id: int,
    currency_id: int,
    logger: SQMLogger,
    noupdate: bool,
    section_types: list[tuple[int, str]],
) -> tuple[bool, int]:
    """
    Process a single template file.

    Returns (success, section_count).
    """
    filename = file_path.name
    stem = file_path.stem  # filename without extension

    logger.log(f'Reading file "{file_path}"')
    logger.progress('T')

    # Parse product line from first 3 chars
    if len(stem) < 3:
        raise ValueError(f"Filename too short to extract product line: {stem}")

    product_line_abbr = stem[:3]
    pl_info = db.lookup_product_line(product_line_abbr)
    if not pl_info:
        raise ValueError(f"Unknown product line abbreviation: '{product_line_abbr}'")

    product_line_id, product_cat_id = pl_info

    # Parse sections from document
    sections = parse_docx_sections(file_path)

    # Log each section found
    for sec in sections:
        logger.log(f"  Section {sec.sequence}: {sec.heading}")
        logger.progress('S')

    # Validate section sequence
    valid, error_msg = validate_section_sequence(sections, product_line_abbr)
    if not valid:
        raise ValueError(f"Section sequence validation failed: {error_msg}")

    if noupdate:
        logger.log("  NOUPDATE mode - skipping database writes")
        return True, len(sections)

    # Read file bytes for blob storage
    file_bytes = file_path.read_bytes()

    # Get or create blob
    blob_id = db.get_or_create_blob(file_bytes, filename)
    logger.log(f"  Blob ID: {blob_id}")

    # Check if template already exists
    existing = db.get_template_by_name(stem)

    if existing:
        plsqt_id = existing['plsqt_id']
        old_blob_id = existing['current_blob_id']
        logger.log(f"  Updating existing template ID: {plsqt_id}")

        # Archive old blob if different
        if old_blob_id and old_blob_id != blob_id:
            db.archive_blob('template', plsqt_id, old_blob_id)
            logger.log(f"  Archived old blob ID: {old_blob_id}")

        # Delete old sections
        deleted = db.delete_template_sections(plsqt_id)
        logger.log(f"  Deleted {deleted} old sections")

        # Update template
        db.update_template(
            plsqt_id=plsqt_id,
            country_id=country_id,
            currency_id=currency_id,
            product_cat_id=product_cat_id,
            product_line_id=product_line_id,
            blob_id=blob_id,
            section_count=len(sections),
            file_path=str(file_path),
        )
    else:
        # Insert new template
        plsqt_id = db.insert_template(
            plsqt_name=stem,
            country_id=country_id,
            currency_id=currency_id,
            product_cat_id=product_cat_id,
            product_line_id=product_line_id,
            blob_id=blob_id,
            section_count=len(sections),
            file_path=str(file_path),
        )
        logger.log(f"  Created new template ID: {plsqt_id}")

    # Insert sections
    for sec in sections:
        # Look up section type by longest-common-substring match
        section_type_id = db.lookup_section_type_by_lcs(sec.heading, section_types)
        if section_type_id is None:
            raise ValueError(f"No section type found for heading: '{sec.heading}'")

        db.insert_section(
            plsqt_id=plsqt_id,
            section_type_id=section_type_id,
            seqn=sec.sequence,
            content=sec.content,
        )

    return True, len(sections)


def main():
    """Main entry point."""
    args = parse_args()
    cfg = load_config(args.ini, args)

    # Construct input path
    input_dir = Path(cfg['path_root']) / cfg['input_folder']

    # Initialize logger
    with SQMLogger(
        log_dir=cfg['log_dir'],
        slug=cfg['log_slug'],
        version=VERSION,
        silent=cfg['silent'],
    ) as logger:

        # Log start
        start_time = datetime.now()
        logger.log(f"SQM Load Quote Template v{VERSION}")
        logger.log(f"Input folder: {input_dir}")
        logger.log(f"Source country: {cfg['country']}, currency: {cfg['currency']}")
        logger.log(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        if cfg['noupdate']:
            logger.log("NOUPDATE mode enabled - no database writes will occur")

        # Discover files
        files = discover_files(input_dir, cfg['skip'], cfg['process'])

        if not files:
            logger.log("No .docx files found in input folder")
            return

        logger.log(f"Found {len(files)} .docx file(s) to process")
        if cfg['skip'] > 0:
            logger.log(f"  (skipped first {cfg['skip']} files)")

        # Database setup
        db_config = DBConfig(
            host=cfg['db_host'],
            port=cfg['db_port'],
            user=cfg['db_user'],
            password=cfg['db_password'],
            database=cfg['db_name'],
        )

        # Statistics
        files_read = 0
        files_stored = 0
        files_failed = 0
        total_sections = 0

        with SQMDatabase(db_config) as db:
            # Cache country and currency IDs
            country_id = db.lookup_country(cfg['country'])
            if country_id is None:
                logger.log(f"Error: Country not found: {cfg['country']}")
                return

            currency_id = db.lookup_currency(cfg['currency'])
            if currency_id is None:
                logger.log(f"Error: Currency not found: {cfg['currency']}")
                return

            logger.log(f"Resolved country_id={country_id}, currency_id={currency_id}")

            # Pre-fetch section types for LCS matching (once, reused for all files)
            section_types = db.fetch_all_section_types()
            logger.log(f"Loaded {len(section_types)} section types for matching")

            # Process each file
            for idx, file_path in enumerate(files, 1):
                try:
                    files_read += 1
                    success, section_count = process_file(
                        file_path=file_path,
                        db=db,
                        country_id=country_id,
                        currency_id=currency_id,
                        logger=logger,
                        noupdate=cfg['noupdate'],
                        section_types=section_types,
                    )

                    if success:
                        if not cfg['noupdate']:
                            db.commit()
                        files_stored += 1
                        total_sections += section_count

                except Exception as e:
                    files_failed += 1
                    db.rollback()
                    logger.log(f"Error processing file #{idx} ({file_path.name}): {e}")

                    if not cfg['continue_on_errors']:
                        logger.log("Halting due to error (CONTINUE_ON_ERRORS=false)")
                        break

        # End summary
        logger.newline()
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        logger.log("=" * 60)
        logger.log("Run Summary")
        logger.log("=" * 60)
        logger.log(f"Start time:       {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.log(f"End time:         {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.log(f"Elapsed:          {elapsed:.1f} seconds")
        logger.log(f"Files read:       {files_read}")
        logger.log(f"Files stored:     {files_stored}")
        logger.log(f"Sections stored:  {total_sections}")
        logger.log(f"Files skipped:    {cfg['skip']}")
        logger.log(f"Files failed:     {files_failed}")

        if cfg['noupdate']:
            logger.log("(NOUPDATE mode - no actual database writes)")


if __name__ == "__main__":
    main()
