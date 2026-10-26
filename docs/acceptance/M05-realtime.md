# M05 长连接 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、Starlette 1.9.0、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.6 长连接模块、2.1.9 WS token 与 WS 连接接口、2.1.10 实时消息类型
- 交付物：
  - `backend/app/core/events.py`（8 种 PRD 事件 + `connected`/`pong`）
  - `backend/app/core/realtime.py`（`ConnectionManager`、`EventPublisher`、`WebSocketPublisher`）
  - `backend/app/workspace/schemas.py`（WS token 请求/响应）
  - `backend/app/workspace/repository.py`（`WebsocketTokenRepository`）
  - `backend/app/workspace/service.py`（`WebSocketTokenService`）
  - `backend/app/workspace/router.py`（`POST /api/chat/ws-token`、`WS /api/chat/ws/chat`）
  - `backend/tests/test_realtime.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 连接管理广播 | 注册假连接后广播任务事件 | 连接收到事件 | 符合预期 | 通过 |
| 2 | WS 握手 | 申请 token 后建立连接 | 收到 `connected` | 符合预期 | 通过 |
| 3 | ping/pong | 发送 `{"type":"ping"}` | 收到 `pong` | 符合预期 | 通过 |
| 4 | 一次性 token | 同一 token 连接两次 | 第二次断开 | 抛出 `WebSocketDisconnect` | 通过 |
| 5 | 非法 token | 使用错误 token 连接 | 连接被拒绝 | 抛出 `WebSocketDisconnect` | 通过 |
| 6 | 未登录申请 token | 不携带 token 调 ws-token | 401 | 返回 401 | 通过 |
| 7 | 会话不存在 | 向不存在会话申请 token | 404 | 返回 404 | 通过 |
| 8 | 会话归属 | 其他用户为会话申请 token | `ConversationNotFound` | 符合预期 | 通过 |
| 9 | 全量测试 | `uv run pytest -q` | 全部通过 | 45 passed | 通过 |
| 10 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] 能申请 ws-token 并建立连接。
- [x] token 只能使用一次。
- [x] 广播只发送到对应会话。
- [x] 断开后连接清理。
- [x] 测试通过。

## 问题与修复

1. **Starlette 1.9 无 `WebSocketException`**：广播异常捕获改为 `OSError`、`RuntimeError`、`WebSocketDisconnect`，避免盲捕 `Exception`。
2. **ruff 导入排序与嵌套 with**：执行 `ruff check --fix` 自动整理。

## 遗留项

- 当前 WS 只处理 `ping/pong`；`user_message` 写入消息并触发分析在 M06 接入。
- 过期或已消费的 token 记录不会主动清理，后续可加定时清理任务。
- 没有心跳超时与服务端主动断开策略。
- 没有单用户连接数限制。

## 结论

通过。
