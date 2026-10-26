# M06 任务 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.4 会话与任务规则、2.1.6 任务模块、2.1.9 任务状态接口、2.1.10 实时事件
- 交付物：
  - `backend/app/analysis/schemas.py`
  - `backend/app/analysis/service.py`（任务 CRUD、状态机、日志、取消、启动恢复）
  - `backend/app/analysis/coordinator.py`（进程内任务编排、事件发布、取消）
  - `backend/app/analysis/router.py`（任务查询、取消）
  - `backend/app/core/database.py`（运行中任务部分唯一索引）
  - `backend/app/main.py`（注册任务路由、启动恢复）
  - `backend/app/workspace/router.py`（WS `user_message` / `cancel` 接入）
  - `backend/tests/test_task.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 成功流程 | 启动任务，FakeRunner 正常返回 | queued→running→success，发布 `done` | 符合预期 | 通过 |
| 2 | 单会话单任务 | 第一个任务运行中再启动第二个 | 抛出 `TaskAlreadyRunning` | 符合预期 | 通过 |
| 3 | 取消运行任务 | 运行中调用取消 | 状态变为 `cancelled`，发布 `done` | 符合预期 | 通过 |
| 4 | 失败流程 | FakeRunner 抛异常 | 状态变为 `failed`，发布 `error`/`done` | 符合预期 | 通过 |
| 5 | 启动恢复 | 预置 running 任务后恢复 | 状态变为 `failed` | 符合预期 | 通过 |
| 6 | 任务查询 | `GET /api/tasks/{task_id}` | 返回 queued 状态 | 符合预期 | 通过 |
| 7 | 任务取消接口 | `POST /api/tasks/{task_id}/cancel` | 返回 cancelled | 符合预期 | 通过 |
| 8 | 任务归属 | 其他用户查询/取消任务 | 查询为空，取消抛 `TaskNotFound` | 符合预期 | 通过 |
| 9 | 全量测试 | `uv run pytest -q` | 全部通过 | 52 passed | 通过 |
| 10 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] 任务状态流转符合 PRD。
- [x] 单运行任务约束生效（应用层检查 + SQLite 部分唯一索引）。
- [x] 取消与失败路径正确。
- [x] 任务查询字段完整。
- [x] 测试通过。

## 问题与修复

1. **唯一索引**：为 `analysis_tasks` 增加“同一会话最多一个 running 任务”的 SQLite 部分唯一索引，并在应用层提前检查 queued/running。
2. **未使用导入**：`coordinator.py` 移除了未使用的 `TaskNotFound`。

## 遗留项

- 协调器的真实 `runner` 尚未接入，M06 阶段由 `FakeRunner` 验证；未配置 runner 时任务会以“分析模块待接入”失败。M07 接入 LangChain 执行器。
- 取消操作同时支持 REST 与 WS；WS 的 `user_message` 已能写入消息并创建任务。
- 进程内 `asyncio` 任务列表不跨进程共享；当前按单进程部署设计。
- 任务日志表已提供 `append_log`，协调器暂未写入详细步骤日志，M07 会补充。

## 结论

通过。
