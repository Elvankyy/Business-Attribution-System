import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "business.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    price REAL NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_exposures (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    exposure_date TEXT NOT NULL,
    exposure_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS product_clicks (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    click_date TEXT NOT NULL,
    click_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS product_conversions (
    id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    conversion_date TEXT NOT NULL,
    order_count INTEGER NOT NULL,
    revenue REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    segment TEXT NOT NULL,
    register_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS visit_events (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    page TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS cart_events (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    order_id TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    source_name,
    content
);
"""

TABLES = (
    "categories",
    "products",
    "search_exposures",
    "product_clicks",
    "product_conversions",
    "customers",
    "visit_events",
    "cart_events",
    "order_events",
    "documents_fts",
)

CATEGORIES = [
    (1, "数码"),
    (2, "家居"),
    (3, "服饰"),
]

PRODUCTS = [
    (1, "无线耳机", 1, 399.0, "active"),
    (2, "智能手表", 1, 899.0, "active"),
    (3, "护眼台灯", 2, 129.0, "active"),
    (4, "收纳盒", 2, 59.0, "active"),
    (5, "运动T恤", 3, 99.0, "active"),
    (6, "跑鞋", 3, 499.0, "active"),
]

SEARCH_EXPOSURES = [
    (10, 1, "2026-08-01", 1600),
    (11, 1, "2026-08-15", 1500),
    (1, 1, "2026-09-01", 1000),
    (2, 1, "2026-09-02", 700),
    (3, 1, "2026-09-03", 400),
    (4, 2, "2026-09-01", 800),
    (5, 2, "2026-09-02", 820),
    (6, 2, "2026-09-03", 810),
    (7, 3, "2026-09-01", 500),
    (8, 3, "2026-09-02", 510),
    (9, 3, "2026-09-03", 520),
]

PRODUCT_CLICKS = [
    (10, 1, "2026-08-01", 160),
    (11, 1, "2026-08-15", 150),
    (1, 1, "2026-09-01", 100),
    (2, 1, "2026-09-02", 60),
    (3, 1, "2026-09-03", 30),
    (4, 2, "2026-09-01", 90),
    (5, 2, "2026-09-02", 92),
    (6, 2, "2026-09-03", 95),
    (7, 3, "2026-09-01", 40),
    (8, 3, "2026-09-02", 42),
    (9, 3, "2026-09-03", 45),
]

PRODUCT_CONVERSIONS = [
    (10, 1, "2026-08-01", 25, 9975.0),
    (11, 1, "2026-08-15", 20, 7980.0),
    (1, 1, "2026-09-01", 20, 7980.0),
    (2, 1, "2026-09-02", 10, 3990.0),
    (3, 1, "2026-09-03", 4, 1596.0),
    (4, 2, "2026-09-01", 15, 13485.0),
    (5, 2, "2026-09-02", 16, 14384.0),
    (6, 2, "2026-09-03", 17, 15283.0),
    (7, 3, "2026-09-01", 8, 1032.0),
    (8, 3, "2026-09-02", 9, 1161.0),
    (9, 3, "2026-09-03", 9, 1161.0),
]

CUSTOMERS = [
    (1, "客户A", "高价值", "2025-01-10"),
    (2, "客户B", "成长型", "2025-03-22"),
    (3, "客户C", "流失风险", "2025-05-08"),
    (4, "客户D", "新客", "2026-08-15"),
    (5, "客户E", "高价值", "2024-11-30"),
]

VISIT_EVENTS = [
    (1, 1, "2026-09-01", "首页", 120),
    (2, 1, "2026-09-02", "商品详情", 300),
    (3, 2, "2026-09-01", "首页", 60),
    (4, 2, "2026-09-03", "购物车", 180),
    (5, 3, "2026-08-20", "首页", 30),
    (6, 3, "2026-08-25", "商品详情", 45),
    (7, 4, "2026-09-03", "首页", 200),
    (8, 5, "2026-09-02", "商品详情", 260),
]

CART_EVENTS = [
    (1, 1, "2026-09-02", 1, 1),
    (2, 1, "2026-09-02", 2, 1),
    (3, 2, "2026-09-03", 3, 2),
    (4, 4, "2026-09-03", 5, 1),
    (5, 5, "2026-09-02", 6, 1),
]

ORDER_EVENTS = [
    (1, 1, "2026-09-02", "SO-1001", 7980.0, "paid"),
    (2, 2, "2026-09-03", "SO-1002", 129.0, "paid"),
    (3, 4, "2026-09-03", "SO-1003", 99.0, "paid"),
    (4, 5, "2026-09-02", "SO-1004", 499.0, "refunded"),
    (5, 3, "2026-08-25", "SO-1005", 59.0, "cancelled"),
]

DOCUMENTS = [
    ("商品目录优化说明", "商品目录优化需要关注搜索曝光、点击和转化数据。"),
    ("无线耳机运营复盘", "无线耳机 8 月大促结束后，9 月搜索曝光和点击明显下降，未安排新的投放。"),
    ("客户行为分析说明", "客户行为分析关注访问、加购和下单事件。"),
    ("退款政策", "退款原因包括质量问题、尺码不符和物流延迟。"),
    ("库存说明", "库存异常通常由入库延迟或销量突增导致。"),
    ("市场投放说明", "市场表现分析需要结合渠道投放与订单销售数据。"),
]


def seed_demo(db_path: str | Path | None = None) -> dict[str, int]:
    path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        for table in TABLES:
            connection.execute(f"DELETE FROM {table}")

        connection.executemany(
            "INSERT INTO categories VALUES (?, ?)", CATEGORIES
        )
        connection.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?)", PRODUCTS
        )
        connection.executemany(
            "INSERT INTO search_exposures VALUES (?, ?, ?, ?)",
            SEARCH_EXPOSURES,
        )
        connection.executemany(
            "INSERT INTO product_clicks VALUES (?, ?, ?, ?)", PRODUCT_CLICKS
        )
        connection.executemany(
            "INSERT INTO product_conversions VALUES (?, ?, ?, ?, ?)",
            PRODUCT_CONVERSIONS,
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS
        )
        connection.executemany(
            "INSERT INTO visit_events VALUES (?, ?, ?, ?, ?)", VISIT_EVENTS
        )
        connection.executemany(
            "INSERT INTO cart_events VALUES (?, ?, ?, ?, ?)", CART_EVENTS
        )
        connection.executemany(
            "INSERT INTO order_events VALUES (?, ?, ?, ?, ?, ?)",
            ORDER_EVENTS,
        )
        connection.executemany(
            "INSERT INTO documents_fts (source_name, content) VALUES (?, ?)",
            DOCUMENTS,
        )
        connection.commit()

        return {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            for table in TABLES
        }
    finally:
        connection.close()


def main() -> None:
    counts = seed_demo()
    print("business.db 初始化完成")
    for table, count in counts.items():
        print(f"- {table}: {count}")


if __name__ == "__main__":
    main()
