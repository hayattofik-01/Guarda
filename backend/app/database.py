from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.resolved_database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


# Columns added after the initial tables shipped. ``create_all`` only creates
# missing tables, never alters existing ones, so we apply these idempotently on
# startup (Postgres supports ADD COLUMN IF NOT EXISTS). New tables are handled
# by ``create_all``.
_COLUMN_MIGRATIONS = (
    "ALTER TABLE targets ADD COLUMN IF NOT EXISTS next_scan_at TIMESTAMPTZ",
    "ALTER TABLE targets ADD COLUMN IF NOT EXISTS last_scan_at TIMESTAMPTZ",
    "ALTER TABLE scans ADD COLUMN IF NOT EXISTS advice TEXT",
    "ALTER TABLE scans ADD COLUMN IF NOT EXISTS advice_status VARCHAR",
    "ALTER TABLE scans ADD COLUMN IF NOT EXISTS advice_source VARCHAR",
    "ALTER TABLE scans ADD COLUMN IF NOT EXISTS devin_session_id VARCHAR",
)


def ensure_schema() -> None:
    """Apply idempotent additive column migrations for the no-Alembic deploy."""
    with engine.begin() as conn:
        for stmt in _COLUMN_MIGRATIONS:
            try:
                conn.execute(text(stmt))
            except Exception:  # noqa: BLE001 - best-effort; never block startup
                pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
