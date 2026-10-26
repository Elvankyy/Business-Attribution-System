# M04 附件 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.3 附件侧栏、2.1.6 附件模块、2.1.8 文件存储、2.1.9 附件接口
- 交付物：
  - `backend/app/workspace/storage.py`（`safe_path`、文件名清洗、上传保存、路径解析、文件删除）
  - `backend/app/workspace/schemas.py`（附件响应模型）
  - `backend/app/workspace/repository.py`（`AttachmentRepository`）
  - `backend/app/workspace/service.py`（`AttachmentService`）
  - `backend/app/workspace/router.py`（附件上传、删除、下载）
  - `backend/tests/test_attachment.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 上传与下载 | 上传 `报告.txt` 后下载 | 200，内容一致 | 符合预期 | 通过 |
| 2 | 路径穿越文件名 | 上传 `../../evil.txt` | 保存为 `evil.txt`，不逃逸 | 符合预期 | 通过 |
| 3 | 会话不存在 | 向不存在会话上传 | 404 | 返回 404 | 通过 |
| 4 | 未登录上传 | 不携带 token 上传 | 401 | 返回 401 | 通过 |
| 5 | 删除附件 | 上传后删除 | 删除成功，再下载 404 | 符合预期 | 通过 |
| 6 | 删除不存在附件 | 删除不存在 ID | 404 | 返回 404 | 通过 |
| 7 | 大小限制 | 超过 `max_bytes` 保存 | 抛出 `ValueError` | 符合预期 | 通过 |
| 8 | 根路径校验 | `safe_path(root, "..", "evil")` | 抛出 `ValueError` | 符合预期 | 通过 |
| 9 | 附件归属 | 其他用户读取/删除附件 | `AttachmentNotFound` | 符合预期 | 通过 |
| 12 | 附件列表 | 上传两个附件后调用 `/api/attachment/ls` | 返回两条附件 | 符合预期 | 通过 |
| 13 | 列表归属 | 不存在的会话或未登录访问列表 | 404 / 401 | 符合预期 | 通过 |
| 10 | 全量测试 | `uv run pytest -q` | 全部通过 | 38 passed | 通过 |
| 11 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] 上传、下载、删除可用。
- [x] 路径校验有效。
- [x] 文件大小限制生效。
- [x] 附件归属校验生效。
- [x] 测试通过。

## 问题与修复

1. **ruff B008**：FastAPI 的 `File(...)` 默认参数触发规范告警；改为 `Annotated[UploadFile, File()]` 与 `Annotated[str, Form()]`。
2. **孤儿文件风险**：文件先落盘、再写数据库；数据库写入失败时补上删除文件的清理逻辑。
3. **异常路径**：数据库中的路径非法或文件缺失时，统一转为 `AttachmentNotFound`，避免 500。

## 遗留项

- `parse_status` 固定为 `pending`，附件文本解析尚未实现；M07 的文本检索暂依赖 `business.db` 文档表。
- 上传接口按 PRD 只接收 `conversation_id`，不直接绑定消息；附件与消息的关联在后续消息/分析流程中补充。
- 当前一次性读取整个文件到内存；超过 50MB 的文件会占用较多内存，后续可改为流式写入。
- 未校验 MIME 类型，仅保存客户端声明的 `content_type`。

## 结论

通过。
