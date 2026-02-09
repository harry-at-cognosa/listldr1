#!/usr/bin/env python3
# cli/batch_load.py - v2.1 - 2026-02-08
# Batch load WAB sales-quote template files (.docx) into the listmgr1 database
# Thin orchestrator that delegates core logic to listldr.service.load_template()

"""
SQM Load Quote Template DOCX File - Batch CLI

Usage:
    python -m cli.batch_load [options]
    python SQM_load_quote_template_docx_file_v2.0.py [options]

See --help for available options.
"""

import argparse
import configparser
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path when run as a script (python cli/batch_load.py)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from listldr.db import SQMDatabase, DBConfig
from listldr.logger import SQMLogger
from listldr.service import load_template


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
                    logger.log(f'Reading file "{file_path}"')
                    logger.progress('T')

                    file_bytes = file_path.read_bytes()
                    result = load_template(
                        file_bytes=file_bytes,
                        filename=file_path.name,
                        db=db,
                        country_id=country_id,
                        currency_id=currency_id,
                        section_types=section_types,
                        update_user="SQM_loader",
                        dry_run=cfg['noupdate'],
                        file_ref=str(file_path),
                    )

                    # Log sections
                    for sec_info in result.sections:
                        logger.log(f"  Section {sec_info.sequence}: {sec_info.heading}")
                        logger.progress('S')

                    if cfg['noupdate']:
                        logger.log("  NOUPDATE mode - skipping database writes")
                    elif result.is_new:
                        logger.log(f"  Created new template ID: {result.plsqt_id}")
                    else:
                        logger.log(f"  Updated existing template ID: {result.plsqt_id}")

                    logger.log(f"  Blob ID: {result.blob_id}")

                    if not cfg['noupdate']:
                        db.commit()
                    files_stored += 1
                    total_sections += result.section_count

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
