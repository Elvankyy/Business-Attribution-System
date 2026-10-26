# M02 会话 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.4 会话与任务规则、2.1.6 会话模块、2.1.9 会话接口、2.1.13 会话管理验收标准
- 交付物：
  - `backend/app/workspace/schemas.py`
  - `backend/app/workspace/storage.py`
  - `backend/app/workspace/repository.py`
  - `backend/app/workspace/service.py`
  - `backend/app/workspace/router.py`
  - `backend/app/main.py`（注册会话路由）
  - `backend/tests/test_conversation.py`
  - `backend/tests/conftest.py`（登录头 fixture、独立测试存储目录）

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 创建与列表 | 调用 `/api/chat/create` 后查询 `/api/chat/ls` | 新会话出现在列表中 | 符合预期 | 通过 |
| 2 | 默认标题 | 创建时不传 title | 标题为“新会话” | 符合预期 | 通过 |
| 3 | 重命名 | 调用 `/api/chat/update` | 标题更新，列表同步 | 符合预期 | 通过 |
| 4 | 更新不存在会话 | 使用不存在的 ID 更新 | 404 | 返回 404 | 通过 |
| 5 | 删除会话 | 调用 `/api/chat/delete` | 返回 deleted=1，列表中消失 | 符合预期 | 通过 |
| 6 | 删除不存在会话 | 使用不存在的 ID 删除 | 返回 deleted=0 | 符合预期 | 通过 |
| 7 | 未登录访问 | 不携带 token 调 `/api/chat/ls` | 401 | 返回 401 | 通过 |
| 8 | 用户归属 | 其他用户查询、修改该会话 | 列表为空，修改被拒绝 | 符合预期 | 通过 |
| 9 | 级联删除 | 预置消息、附件、任务、结果、摘要、WS token、任务日志后删除会话 | 子表记录全部删除 | 全部为 0 | 通过 |
| 10 | 存储目录清理 | 预置 uploads/exports/workspace 目录后删除会话 | 三类目录全部删除 | 全部不存在 | 通过 |
| 11 | 全量测试 | `uv run pytest -q` | 全部通过 | 21 passed | 通过 |
| 12 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |
| 13 | 真实 HTTP 冒烟 | 启动 uvicorn，走创建/列表/更新/删除 | 200，列表状态正确 | 全部符合预期 | 通过 |

## 验收标准核对

- [x] 四个会话接口按 PRD 字段返回。
- [x] 会话归属校验生效。
- [x] 删除级联完整。
- [x] 会话状态取值符合 `active/archived/deleted`。
- [x] 测试通过。

## 问题与修复

1. **方法名遮蔽内置 `list`**：`ConversationService.list` 导致类体内 `list[str]` 注解解析失败。已重命名为 `list_for_user`。
2. **测试存储目录断言过窄**：M02 为测试隔离改用 `test_storage`，原 M00 断言写死 `storage`。已改为断言路径为绝对路径。

## 遗留项

- 当前删除为物理删除；`deleted` 状态保留但未使用。若后续需要软删除或归档，再单独设计。
- `last_message_at` 在 M02 不更新，等 M03 消息模块写入消息时维护。
- `storage.py` 目前只负责删除目录；路径穿越校验与上传保存放在 M04。
- 批量删除会跳过不存在或不属于当前用户的 ID，只返回实际删除数量；不返回逐条错误。

## 结论

通过。
