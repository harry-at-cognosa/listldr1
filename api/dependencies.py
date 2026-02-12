"""
FastAPI dependency injection for DB connections, cached data, and logging.
"""

from typing import Generator

from fastapi import Depends, Request

from listldr.db import SQMDatabase
from listldr.logger import SQMLogger


def get_db(request: Request) -> Generator[SQMDatabase, None, None]:
    """
    Yield an SQMDatabase backed by a pooled connection.

    Commits on success, rolls back on exception, and returns the
    connection to the pool when done.
    """
    pool = request.app.state.db_pool
    conn = pool.getconn()
    db = SQMDatabase(conn=conn)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        pool.putconn(conn)


def get_section_types(request: Request) -> list[tuple[int, str]]:
    """Return the cached section_types list from app state."""
    return request.app.state.section_types


def get_logger(request: Request) -> SQMLogger:
    """Return the shared SQMLogger instance from app state."""
    return request.app.state.logger
