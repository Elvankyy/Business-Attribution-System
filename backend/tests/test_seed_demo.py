import pytest

from app.analysis.harness.tools import SqlQueryTool, TextSearchTool
from scripts.seed_demo import seed_demo


def test_seed_demo_is_idempotent(tmp_path):
    path = tmp_path / "business.db"

    first = seed_demo(path)
    second = seed_demo(path)

    assert first == second
    assert first["products"] > 0
    assert first["customers"] > 0
    assert first["documents_fts"] > 0


@pytest.mark.asyncio
async def test_seeded_data_is_queryable(tmp_path):
    path = tmp_path / "business.db"
    seed_demo(path)

    sql_tool = SqlQueryTool(
        str(path),
        {"products", "product_conversions"},
        max_rows=10,
        timeout_seconds=2,
    )
    result = await sql_tool.run(
        "SELECT p.name, SUM(c.revenue) AS revenue "
        "FROM products p "
        "JOIN product_conversions c ON c.product_id = p.id "
        "GROUP BY p.name ORDER BY revenue DESC"
    )

    assert result.success is True
    assert len(result.data["rows"]) > 0

    text_tool = TextSearchTool(str(path))
    text_result = await text_tool.run("退款")

    assert text_result.success is True
    assert len(text_result.data["results"]) > 0
