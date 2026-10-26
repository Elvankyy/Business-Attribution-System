# M07 分析 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、LangChain 1.4.7、langchain-deepseek 1.1.1、SQLAlchemy 2.1.6、SQLite（FTS5）
- 关联需求：PRD 2.1.6 分析模块、2.1.10 实时事件、2.1.11 分析输出格式
- 交付物：
  - `backend/app/analysis/agent/output.py`（六段式输出契约）
  - `backend/app/analysis/agent/prompt.py`
  - `backend/app/analysis/agent/factory.py`（DeepSeek 懒加载、`create_agent`、`ToolStrategy`）
  - `backend/app/analysis/harness/runtime.py`
  - `backend/app/analysis/harness/context.py`
  - `backend/app/analysis/harness/tools.py`（SQL 查询、FTS5 检索、ToolExecutor）
  - `backend/app/analysis/harness/validator.py`
  - `backend/app/analysis/harness/executor.py`（流式执行、纠错重试、真实 Runner）
  - `backend/app/main.py`（启动时装配真实 Runner）
  - `backend/tests/test_analysis.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | SQL 查询与行数限制 | 查询 `orders`，`max_rows=2` | 成功，最多 2 行 | 符合预期 | 通过 |
| 2 | SQL 安全 | 非白名单表、DELETE、多语句、注释、空 SQL | 全部拒绝 | 全部失败 | 通过 |
| 3 | FTS5 检索 | 检索“退款” | 返回 `doc1` | 符合预期 | 通过 |
| 4 | 输出校验 | 合法输出、伪造证据来源、建议不足 2 条 | 合法通过，非法报错 | 符合预期 | 通过 |
| 5 | 流式执行 | FakeAgent 输出 token 与结构化结果 | 发布 `message_delta`，返回六段式 | 符合预期 | 通过 |
| 6 | 纠错重试 | 第一次证据来源非法，第二次合法 | 重试 1 次后通过 | 符合预期 | 通过 |
| 7 | 无 Key 行为 | 未配置 `DEEPSEEK_API_KEY` 调 `create_model` | 抛出明确错误 | 符合预期 | 通过 |
| 8 | Agent 构造 | 用假 DeepSeek 模型构造真实 agent | 构造成功 | 符合预期 | 通过 |
| 9 | 工具落库 | ToolExecutor 执行 SQL | 写 tool 消息与任务日志，发工具事件 | 符合预期 | 通过 |
| 10 | 上下文编译 | 会话含历史与摘要 | 摘要进入 system，当前问题在最后 | 符合预期 | 通过 |
| 11 | 全量测试 | `uv run pytest -q` | 全部通过 | 62 passed | 通过 |
| 12 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |

## 验收标准核对

- [x] 上下文包含历史、摘要与附件名称。
- [x] 工具调用经过 ToolExecutor 并留下记录。
- [x] 结构化输出包含六段式字段。
- [x] 证据可追溯校验生效。
- [x] 纠错重试不超过配置次数。
- [x] 无 Key 时返回明确错误，不崩溃。
- [x] SQL 工具只读、白名单、LIMIT、超时。
- [x] FTS5 文本检索可用。

## 问题与修复

1. **中文 FTS5 匹配不到**：默认分词把整句中文作为一个 token，精确短语匹配失败。改为前缀查询（`"关键词"*`），兼容中文关键词。
2. **Starlette/LangChain 版本差异**：先确认 `create_agent`、`ToolStrategy`、`ToolCallLimitMiddleware` 与 `ChatDeepSeek` 的实际签名后再实现，避免沿用旧版写法。
3. **OpenCode Zen 接入适配**：base URL 需要 `/v1`，请求必须带 `x-opencode-session`；thinking 模式不支持强制 `tool_choice`，已传 `thinking={"type":"disabled"}`。
4. **工具并发与模型收敛**：消息写入增加 `seq_no` 冲突重试；系统提示注入业务表字段摘要；提高递归上限并按工具限制调用次数。

## 遗留项

- 真实模型调用已于 2026-10-24 通过 OpenCode Zen（`deepseek-v4.1-flash`）验证，见 [E2E-01](E2E-01-product-catalog.md) 与 [E2E-02](E2E-02-customer-behavior.md)；单元测试仍使用假模型验证构造与流式执行。
- 分析结果由 M08 落库；当前 Coordinator 只把任务标记为成功，尚未写 `analysis_results` 与发送 `result_ready`。
- 附件文本解析尚未实现，上下文目前只带附件名称；文本检索依赖 `documents_fts` 表。
- SQL 工具只允许单条 SELECT，不支持 CTE；分析复杂问题时可在后续放宽并补充校验。
- 工具日志已写入 `messages` 与 `task_logs`，但详细执行耗时目前只写在日志文本中。

## 结论

通过。
