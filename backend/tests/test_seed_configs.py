import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.models import SystemConfig
from scripts.seed_configs import seed_configs


@pytest.mark.asyncio
async def test_seed_configs_is_idempotent():
    first = await seed_configs()
    second = await seed_configs()

    assert first == second

    async with SessionLocal() as session:
        rows = (
            await session.execute(select(SystemConfig))
        ).scalars().all()

    keys = {row.config_key for row in rows}
    assert "data_source.main" in keys
    assert "feature.command_tool" in keys
