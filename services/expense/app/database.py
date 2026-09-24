from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base

_settings = get_settings()
engine = create_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

# (746201, 926) is the ClaimGuard schema-initialization advisory lock
# (pg_advisory_xact_lock class, id).
_SCHEMA_LOCK_CLASS = 746201
_SCHEMA_LOCK_ID = 926


def init_schema() -> None:
    """Create tables if they do not exist, serialized across Expense replicas.

    PostgreSQL CREATE TABLE / CREATE TYPE is not safe under concurrent create_all()
    (UniqueViolation on pg_type_typname_nsp_index). An advisory transaction lock
    on this connection makes replicas wait, then create_all() sees existing objects.
    create_all() must use this same connection, not the Engine, or it would take a
    different pooled session and bypass the lock.
    """
    with engine.begin() as connection:
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:lock_class, :lock_id)"),
            {"lock_class": _SCHEMA_LOCK_CLASS, "lock_id": _SCHEMA_LOCK_ID},
        )
        Base.metadata.create_all(bind=connection)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
