"""
Configuration factories for the SQM template loader.

Provides DBConfig construction from environment variables or INI files.
"""

import configparser
import os
from pathlib import Path

from listldr.db import DBConfig


def db_config_from_env() -> DBConfig:
    """
    Build a DBConfig from environment variables.

    Expected vars: LISTLDR_DB_HOST, LISTLDR_DB_PORT, LISTLDR_DB_USER,
                   LISTLDR_DB_PASSWORD, LISTLDR_DB_NAME
    """
    return DBConfig(
        host=os.environ.get("LISTLDR_DB_HOST", "localhost"),
        port=int(os.environ.get("LISTLDR_DB_PORT", "5432")),
        user=os.environ.get("LISTLDR_DB_USER", "postgres"),
        password=os.environ.get("LISTLDR_DB_PASSWORD", ""),
        database=os.environ.get("LISTLDR_DB_NAME", "listmgr1"),
    )


def db_config_from_ini(ini_path: str | Path) -> DBConfig:
    """Build a DBConfig from an INI file's [database] section."""
    config = configparser.ConfigParser()
    config.read(ini_path)
    return DBConfig(
        host=config.get("database", "host"),
        port=config.getint("database", "port"),
        user=config.get("database", "user"),
        password=config.get("database", "password"),
        database=config.get("database", "database"),
    )
