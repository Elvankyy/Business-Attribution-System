import asyncio
import os
import shutil
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB = BACKEND_DIR / "data" / "test_app.db"
TEST_STORAGE = BACKEND_DIR / "data" / "test_storage"

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB.as_posix()}"
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["STORAGE_ROOT"] = str(TEST_STORAGE)


@pytest.fixture(scope="session", autouse=True)
def clean_test_environment():
    for suffix in ("", "-wal", "-shm"):
        Path(str(TEST_DB) + suffix).unlink(missing_ok=True)
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)
    yield
    from app.core.database import dispose_engine

    asyncio.run(dispose_engine())
    for suffix in ("", "-wal", "-shm"):
        Path(str(TEST_DB) + suffix).unlink(missing_ok=True)
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def db_session() -> AsyncIterator:
    from app.core.database import SessionLocal, init_database

    await init_database()
    async with SessionLocal() as session:
        yield session


@pytest.fixture
def auth_headers(client) -> dict[str, str]:
    login = client.get("/auth/login", follow_redirects=False)
    state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
    callback = client.get(
        "/auth/callback",
        params={"code": "demo", "state": state},
        follow_redirects=False,
    )
    token = callback.headers["location"].split("#token=", 1)[1]
    return {"Authorization": f"Bearer {token}"}
