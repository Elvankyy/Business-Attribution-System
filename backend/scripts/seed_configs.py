import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal, init_database
from app.core.models import SystemConfig

CONFIGS = [
    ("data_source.main", "sqlite:///data/business.db", "data_source"),
    ("data_source.audit", "sqlite:///data/app.db", "data_source"),
    ("feature.command_tool", "false", "feature"),
    ("feature.external_search", "false", "feature"),
    ("feature.export_markdown", "true", "feature"),
]


async def seed_configs() -> dict[str, int]:
    await init_database()
    async with SessionLocal() as session:
        for key, value, group in CONFIGS:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            row = result.scalar_one_or_none()
            if row is None:
                session.add(
                    SystemConfig(
                        config_key=key,
                        config_value=value,
                        config_group=group,
                    )
                )
            else:
                row.config_value = value
                row.config_group = group
        await session.commit()

    return {"configs": len(CONFIGS)}


def main() -> None:
    print(asyncio.run(seed_configs()))


if __name__ == "__main__":
    main()
