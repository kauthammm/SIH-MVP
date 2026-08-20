"""Database — CSV mode by default for local demo (no PostgreSQL required)."""
from __future__ import annotations

import os

from app.config import get_settings
from app.services import csv_store

settings = get_settings()

# Local demo: CSV files only. Set USE_POSTGRES=true in .env to enable PostgreSQL.
USE_CSV = os.getenv("USE_POSTGRES", "").lower() not in ("1", "true", "yes")

if USE_CSV:
    engine = None
    SessionLocal = None
    Base = object  # type: ignore

    def get_db():
        yield None
else:
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker, DeclarativeBase

        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        class Base(DeclarativeBase):
            pass

        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
    except Exception:
        USE_CSV = True
        engine = None
        SessionLocal = None
        Base = object  # type: ignore

        def get_db():
            yield None
