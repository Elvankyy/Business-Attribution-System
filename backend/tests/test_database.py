import pytest
from sqlalchemy import inspect

from app.core.database import engine, init_database

EXPECTED_TABLES = {
    "users",
    "conversations",
    "messages",
    "attachments",
    "analysis_tasks",
    "analysis_results",
    "context_summaries",
    "websocket_tokens",
    "system_configs",
    "task_logs",
}


@pytest.mark.asyncio
async def test_all_tables_created():
    await init_database()

    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: set(inspect(sync_conn).get_table_names())
        )

    assert EXPECTED_TABLES <= tables


@pytest.mark.asyncio
async def test_sqlite_pragmas():
    await init_database()

    async with engine.connect() as conn:
        foreign_keys = (await conn.exec_driver_sql("PRAGMA foreign_keys")).scalar()
        journal_mode = (await conn.exec_driver_sql("PRAGMA journal_mode")).scalar()
        busy_timeout = (await conn.exec_driver_sql("PRAGMA busy_timeout")).scalar()

    assert foreign_keys == 1
    assert str(journal_mode).lower() == "wal"
    assert busy_timeout == 5000
