# M10 示例数据 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、SQLite（FTS5）、SQLAlchemy 2.1.6
- 关联需求：PRD 2.1.12 示例业务场景要求、2.1.13 完整演示链路
- 交付物：
  - `backend/scripts/seed_demo.py`
  - 项目根 `.env.example`（`SQL_ALLOWED_TABLES` 白名单）
  - `backend/tests/test_seed_demo.py`

## 示例场景

| 场景 | 表 |
|---|---|
| 商品目录优化 | `categories`、`products`、`search_exposures`、`product_clicks`、`product_conversions` |
| 客户行为分析 | `customers`、`visit_events`、`cart_events`、`order_events` |
| 文本检索 | `documents_fts` |

生成结果：商品 6 条、类目 3 条、曝光/点击/转化各 11 条、客户 5 条、访问 8 条、加购 5 条、订单 5 条、文档 6 条。

真实链路验收：[E2E-01 商品目录优化](E2E-01-product-catalog.md)、[E2E-02 客户行为分析](E2E-02-customer-behavior.md)。

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 种子幂等 | 连续执行两次 `seed_demo` | 两次计数一致 | 符合预期 | 通过 |
| 2 | 业务表生成 | 检查 `business.db` | 两个场景表均有数据 | 符合预期 | 通过 |
| 3 | SQL 工具查询 | 用 SQL 工具统计商品收入 | 查询成功并返回行 | 符合预期 | 通过 |
| 4 | FTS5 检索 | 检索“退款” | 命中示例文档 | 符合预期 | 通过 |
| 5 | 全量测试 | `uv run pytest -q` | 全部通过 | 74 passed | 通过 |
| 6 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] `business.db` 包含两个场景所需表。
- [x] 种子脚本可重复执行。
- [x] 分析工具可直接查询示例数据。
- [x] FTS5 文本检索可用。
- [x] 两个场景的真实 LLM 全链路演示（2026-10-24 通过 OpenCode Zen + `deepseek-v4.1-flash`，见 E2E-01/E2E-02）。
- [x] 结果导出能力已由 M08 验证。

## 演示步骤

```powershell
# 在项目根目录
Copy-Item .env.example .env
# 在根 .env 中填写 DEEPSEEK_API_KEY

cd backend
uv run python -m scripts.seed_demo
uv run uvicorn app.main:app --reload --port 8000
```

1. 登录后创建会话。
2. 场景一提问：`为什么无线耳机最近销量下降？`
3. 场景二提问：`哪些客户有流失风险，原因是什么？`
4. 观察 WebSocket 的工具执行、流式文本与最终六段式结果。
5. 下载 Markdown 结果文件。

## 问题与修复

1. **中文控制台输出**：Git Bash 捕获时中文显示为乱码，但数据与文件写入正常；PowerShell/UTF-8 终端下正常。

## 遗留项

- 当前只实现了 PRD 要求的最少两个场景；库存、评论、市场、退款四个场景可在后续扩展。
- 示例数据为合成数据，不代表真实业务分布。
- 附件文本解析未实现，文本检索目前基于 `documents_fts`。
- 文本检索对多关键词采用 AND 语义，部分自然语言查询可能返回 0 条；后续可改为 OR 或 trigram 分词。

## 结论

通过（数据、工具与真实模型链路均已验证）。
