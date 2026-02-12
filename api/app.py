"""
FastAPI application for the SQM template loader.

Start with:
    uvicorn api.app:app --reload
"""

from contextlib import asynccontextmanager

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg2.pool import ThreadedConnectionPool

from listldr.config import db_config_from_env
from listldr.db import SQMDatabase
from listldr.logger import SQMLogger
from api.routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage DB pool and cached lookups across app lifetime."""
    cfg = db_config_from_env()

    # Create connection pool (min 1, max 10 connections)
    pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
    )
    app.state.db_pool = pool

    # Pre-fetch section types (cached for the lifetime of the app)
    conn = pool.getconn()
    try:
        db = SQMDatabase(conn=conn)
        app.state.section_types = db.fetch_all_section_types()
    finally:
        pool.putconn(conn)

    # Start request logger
    origins = os.environ.get("LISTLDR_CORS_ORIGINS", "http://localhost:3000")
    logger = SQMLogger(log_dir="./log", slug="API_services", version="01", silent=False)
    app.state.logger = logger
    logger.log("=== SQM Template Loader API v1.0.0 starting ===")
    logger.log(f"DB host: {cfg.host}:{cfg.port}/{cfg.database}")
    logger.log(f"CORS origins: {origins}")
    logger.log(f"Section types cached: {len(app.state.section_types)}")

    yield

    # Shutdown: log uptime, close logger, close pool
    logger.log(f"=== Shutting down (uptime {logger.elapsed_seconds:.1f}s) ===")
    logger.close()
    pool.closeall()


app = FastAPI(
    title="SQM Template Loader API",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("LISTLDR_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
