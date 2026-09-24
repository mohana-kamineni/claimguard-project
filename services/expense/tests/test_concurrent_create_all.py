"""Requires PostgreSQL (see repo README). Simulates several Expense replicas starting together."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import inspect, text

from app.database import engine, init_schema
from app.models import Base


def test_concurrent_create_all_from_multiple_replicas():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        connection.commit()

    def replica_startup() -> None:
        init_schema()

    errors = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(replica_startup) for _ in range(4)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 — collect all replica failures
                errors.append(exc)

    assert errors == []
    table_names = inspect(engine).get_table_names()
    assert "claims" in table_names
    # Second wave of replica starts must still be idempotent.
    init_schema()
    assert "claims" in inspect(engine).get_table_names()
    assert "claims" in Base.metadata.tables
