"""Database connection wiring.

The connection string comes from `DATABASE_URL` (see `app/config.py`) -- never hard-coded.
`engine`/`SessionLocal` are None until a URL is configured so importing this module (e.g. to
build the ORM models) never requires a live database.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True) if settings.database_url else None

SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine is not None else None
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
