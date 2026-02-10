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

    yield

    # Shutdown: close all pooled connections
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
