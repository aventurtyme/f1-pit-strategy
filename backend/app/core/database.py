"""
backend/app/core/database.py

Sync SQLAlchemy engine using pg8000 driver.
This is intentionally identical to the existing database.py — no changes
needed here. Reproduced so the full backend folder is self-contained.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

Base = declarative_base()

# Set DATABASE_ECHO=true in .env to log all SQL — useful during development
_echo = os.getenv("DATABASE_ECHO", "false").lower() == "true"


def get_engine():
    return create_engine(DATABASE_URL, echo=_echo)


def get_session_local():
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy Session and guarantees
    it is closed whether the request succeeds or raises.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()