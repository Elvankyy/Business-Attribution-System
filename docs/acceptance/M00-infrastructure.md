# M00 基础设施 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、uv 0.12.0、FastAPI 0.161.1、SQLAlchemy 2.1.6、aiosqlite 0.22.1、SQLite
- 关联需求：PRD 2.1.1 基础能力、2.1.7 数据表、2.1.13 验收标准中的服务启动与数据基础
- 交付物：
  - `backend/pyproject.toml`
  - 项目根 `.env.example`（统一配置）
  - `backend/app/main.py`
  - `backend/app/core/config.py`
  - `backend/app/core/database.py`
  - `backend/app/core/models.py`
  - `backend/app/core/dependencies.py`
  - `backend/scripts/init_db.py`
  - `backend/tests/`（config、database、health）
  - `backend/start.ps1`、`backend/stop.ps1`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 依赖安装 | `uv sync` | 依赖安装成功 | 成功，70 个包解析完成 | 通过 |
| 2 | 配置加载 | `uv run pytest tests/test_config.py` | 默认值与存储路径正确 | 2 个测试通过 | 通过 |
| 3 | 数据库建表 | `uv run python -m scripts.init_db` | 创建 10 张表 | 10 张表全部创建 | 通过 |
| 4 | SQLite PRAGMA | `uv run pytest tests/test_database.py` | `foreign_keys=1`、`journal_mode=wal`、`busy_timeout=5000` | 全部符合 | 通过 |
| 5 | 健康检查 | 启动 uvicorn 后请求 `/health` | 返回 `status=ok`、`database=sqlite`、`llm_configured=false` | 返回符合预期 | 通过 |
| 6 | 接口文档 | 请求 `/docs` 与 `/openapi.json` | 200，标题为 Business Attribution System | 200，标题正确 | 通过 |
| 7 | 存储目录 | 检查 `storage/` | `uploads`、`exports`、`workspace` 存在 | 三个目录存在 | 通过 |
| 8 | 单元测试 | `uv run pytest -q` | 全部通过 | 6 passed | 通过 |
| 9 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] `uv run uvicorn app.main:app` 启动成功。
- [x] `data/app.db` 自动生成且包含 10 张表。
- [x] `GET /health` 返回正常状态。
- [x] `GET /docs` 可访问。
- [x] `uv run pytest tests/test_health.py` 通过。
- [x] SQLite PRAGMA 生效。
- [x] 无 DeepSeek Key 时服务正常启动。

## 问题与修复

1. **缺少 greenlet**：SQLAlchemy 异步模式导入失败。将依赖改为 `sqlalchemy[asyncio]`，安装 greenlet 后通过。
2. **测试库文件被占用**：退出时无法删除 `test_app.db`。在应用 lifespan 与测试清理逻辑中释放 engine 后通过。
3. **ruff 规范问题**：导入排序、`datetime.UTC`、`__all__` 排序。执行 `ruff check --fix` 后通过。

## 遗留项

- `backend/data/app.db` 是本地运行文件，不提交仓库。
- 当前未引入数据库迁移工具；开发阶段表结构变更直接删除 `app.db` 重建。
- M01 及后续模块尚未实现。

## 结论

通过。
