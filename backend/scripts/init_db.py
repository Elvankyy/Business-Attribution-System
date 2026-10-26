import asyncio

from sqlalchemy import inspect

from app.core.database import engine, init_database


async def main() -> None:
    await init_database()
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: sorted(inspect(sync_conn).get_table_names())
        )
    print("数据库初始化完成")
    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    asyncio.run(main())
