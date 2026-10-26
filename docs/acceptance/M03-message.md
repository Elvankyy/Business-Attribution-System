# M03 消息 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.3 聊天工作台、2.1.6 消息模块、2.1.9 历史消息接口
- 交付物：
  - `backend/app/workspace/schemas.py`（消息与附件响应模型）
  - `backend/app/workspace/repository.py`（`MessageRepository`）
  - `backend/app/workspace/service.py`（`MessageService`）
  - `backend/app/workspace/router.py`（`GET /api/chat/ls/{conversation_id}`）
  - `backend/tests/test_message.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 消息顺序 | 连续写入 user、tool、assistant 消息 | `seq_no` 为 1、2、3 | 符合预期 | 通过 |
| 2 | 工具消息 | 写入工具消息 | `tool_name`、`tool_status` 保存正确 | 符合预期 | 通过 |
| 3 | 会话时间 | 写入消息后查询会话 | `last_message_at` 已更新 | 符合预期 | 通过 |
| 4 | 历史查询 | 读取会话历史 | 按 `seq_no` 升序返回 | 符合预期 | 通过 |
| 5 | 附件关联 | 消息关联附件后读取历史 | 附件出现在对应消息下 | 符合预期 | 通过 |
| 6 | 归属校验 | 其他用户读取历史 | 抛出 `ConversationNotFound` | 符合预期 | 通过 |
| 7 | 非法角色 | 写入 `invalid` 角色 | 抛出 `ValueError` | 符合预期 | 通过 |
| 8 | 空会话历史 | 新会话调用历史接口 | 返回 `[]` | 符合预期 | 通过 |
| 9 | 不存在会话 | 调用不存在会话的历史接口 | 404 | 返回 404 | 通过 |
| 10 | 未登录 | 不携带 token 调用历史接口 | 401 | 返回 401 | 通过 |
| 11 | API 序列化 | 写入消息后通过接口读取 | 返回消息与空附件列表 | 符合预期 | 通过 |
| 12 | 全量测试 | `uv run pytest -q` | 全部通过 | 29 passed | 通过 |
| 13 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] 消息写入后可按顺序回放。
- [x] `seq_no` 无重复、无回退。
- [x] 工具消息可区分。
- [x] 历史接口字段符合 PRD。
- [x] 测试通过。

## 问题与修复

1. **方法名遮蔽内置 `list`**：M02 的 `ConversationService.list` 导致 M03 的类型注解解析失败；已在 M02 阶段重命名为 `list_for_user`。
2. **测试变量未使用**：`test_history_ownership` 中 `owner` 未使用，ruff 报 `RUF059`；改为 `_owner`。

## 遗留项

- `seq_no` 当前用 `max(seq_no)+1` 分配，依赖单会话串行执行；如后续出现并发写入，需要使用事务重试或独立序列。
- 历史接口目前一次性返回全部消息，未分页；消息量很大时再补分页参数。
- 用户消息的 WebSocket 写入入口在 M05/M06 接入，本模块只提供 Service 方法。
- 附件文件保存与路径校验在 M04 实现。

## 结论

通过。
