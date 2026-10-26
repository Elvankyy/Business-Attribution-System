# 经营归因分析系统 — 后端开发说明

## 1. 项目概览

面向经营分析场景的多轮归因分析系统。用户完成授权登录后，在聊天工作台创建会话、上传资料、提出业务问题；系统调用分析工具处理数据，通过 WebSocket 实时推送分析过程，最终输出六段式结构化结论并支持导出。

六段式结果：

1. 问题定义
2. 关键指标（数组：`metric_name`、`metric_value`、`metric_unit`、`metric_period`）
3. 证据列表（数组：`source_type`、`source_name`、`evidence_text`、`related_metric`、`confidence`）
4. 归因结论
5. 待补充数据
6. 下一步建议（至少 2 条）

## 2. 技术栈

| 层次 | 技术 |
|---|---|
| 语言 | Python 3.12 |
| Web 框架 | FastAPI + Uvicorn |
| 数据访问 | SQLAlchemy 2.x（async）+ aiosqlite |
| 数据校验 | Pydantic v2 + pydantic-settings |
| 认证 | PyJWT（HS256），内置 Demo 认证中心，预留真实认证中心适配器 |
| 文件上传 | python-multipart |
| 外部调用 | httpx |
| AI 编排 | LangChain 1.x `create_agent` |
| 模型接入 | `langchain-deepseek`（`ChatDeepSeek`）+ OpenCode Zen OpenAI 兼容网关（`deepseek-v4.1-flash`） |
| 数据库 | SQLite：系统表 `app.db`，业务数据 `business.db` |
| 文本检索 | SQLite FTS5 |
| 依赖管理 | uv |
| 测试与规范 | pytest + pytest-asyncio + ruff |

## 3. 后端目录结构

> 统一配置：项目根目录 `.env` / `.env.example` 同时供后端与前端读取；后端 `app/core/config.py` 与 Vite `envDir` 都指向根文件，子目录不再维护 `.env`。

```
backend/
├─ pyproject.toml
├─ start.ps1 / stop.ps1
├─ data/                         # app.db、business.db
├─ storage/
│  ├─ uploads/                   # 附件
│  ├─ exports/                   # 导出结果
│  └─ workspace/                 # 临时文件
├─ app/
│  ├─ main.py                    # create_app、lifespan、CORS、路由注册
│  ├─ core/
│  │  ├─ config.py               # Settings + get_settings
│  │  ├─ database.py             # engine / session / SQLite PRAGMA
│  │  ├─ models.py               # 10 张表
│  │  ├─ dependencies.py         # get_current_user、Service 依赖
│  │  ├─ realtime.py             # ConnectionManager + EventPublisher
│  │  └─ events.py               # 8 种实时事件
│  ├─ auth/
│  │  ├─ router.py               # 登录、回调
│  │  ├─ schemas.py
│  │  ├─ service.py              # JWT、state、用户 upsert
│  │  └─ adapter.py              # AuthCenterAdapter + DemoAuthCenter
│  ├─ workspace/
│  │  ├─ router.py               # chat、附件、ws-token、WS、结果查询
│  │  ├─ schemas.py
│  │  ├─ service.py              # 会话、消息、附件、结果
│  │  ├─ repository.py
│  │  └─ storage.py              # 路径校验、上传保存、目录删除
│  ├─ analysis/
│  │  ├─ router.py               # 任务状态查询
│  │  ├─ schemas.py
│  │  ├─ service.py              # 任务、结果 CRUD
│  │  ├─ coordinator.py          # 任务生命周期、进程内 asyncio
│  │  ├─ agent/
│  │  │  ├─ factory.py           # create_model / create_analysis_agent
│  │  │  ├─ prompt.py            # 六段式系统提示词
│  │  │  └─ output.py            # AnalysisOutput / KeyMetric / Evidence
│  │  └─ harness/
│  │     ├─ runtime.py           # AgentRuntimeContext / 执行状态
│  │     ├─ context.py           # 历史 + 摘要 + 附件文本
│  │     ├─ executor.py          # astream、重试、用量
│  │     ├─ validator.py         # 结构 + 证据追溯校验
│  │     └─ tools.py             # ToolExecutor + SQL 查询 + FTS5 检索
│  └─ admin/
│     ├─ router.py               # 配置重载
│     ├─ schemas.py
│     └─ service.py              # 配置、日志
├─ scripts/
│  ├─ init_db.py
│  └─ seed_demo.py
└─ tests/
   └─ test_health.py
```

## 4. 九个后端模块与文件落点

| 序号 | PRD 模块 | 主要文件 |
|---|---|---|
| 1 | 认证接入模块 | `app/auth/router.py`、`app/auth/schemas.py`、`app/auth/service.py`、`app/auth/adapter.py`、`app/core/dependencies.py` |
| 2 | 会话模块 | `app/workspace/router.py`、`app/workspace/schemas.py`、`app/workspace/service.py`、`app/workspace/repository.py` |
| 3 | 消息模块 | `app/workspace/router.py`、`app/workspace/service.py`、`app/workspace/repository.py` |
| 4 | 附件模块 | `app/workspace/router.py`、`app/workspace/service.py`、`app/workspace/storage.py` |
| 5 | 长连接模块 | `app/core/realtime.py`、`app/core/events.py`、`app/workspace/router.py` |
| 6 | 任务模块 | `app/analysis/router.py`、`app/analysis/schemas.py`、`app/analysis/service.py`、`app/analysis/coordinator.py` |
| 7 | 分析模块 | `app/analysis/agent/`、`app/analysis/harness/`、`app/analysis/coordinator.py` |
| 8 | 结果模块 | `app/analysis/service.py`、`app/workspace/router.py`、`app/workspace/service.py` |
| 9 | 配置模块 | `app/core/config.py`、`app/admin/router.py`、`app/admin/service.py` |

## 5. 模块详情

### 5.1 认证接入模块

职责：对接认证中心、令牌校验、当前用户识别。

接口：
- `GET /auth/login`：生成签名 state，跳转认证中心授权页；Demo 模式支持 `?as_admin=true` 登录管理员。
- `GET /auth/callback`：校验 state，换取用户信息，签发 JWT，重定向前端。
- `GET /api/me`：返回当前登录用户信息，供前端登录态校验。

数据表：`users`。

关键约束：
- `AuthCenterAdapter` 定义 `build_authorize_url(state)` 与 `exchange_code(code)`。
- `DemoAuthCenter` 提供本地授权流程；真实认证中心只替换适配器。
- JWT 使用 HS256，`sub` 为用户 ID，密钥来自 `.env`。
- 路由通过 `get_current_user` 解析 Bearer Token，不信任前端传入的用户 ID。

### 5.2 会话模块

职责：会话的新增、查询、更新、删除。

接口：
- `POST /api/chat/create`：请求 `title`，响应 `conversation_id`、`title`、`status`。
- `POST /api/chat/delete`：请求 `conversation_ids`。
- `POST /api/chat/update`：请求 `conversation_id`、`title`。
- `GET /api/chat/ls`：响应 `conversation_id`、`title`、`status`、`last_message_at`。

数据表：`conversations`。

关键约束：
- 会话状态：`active`、`archived`、`deleted`。
- 删除会话必须级联删除消息、附件、任务、结果、上下文摘要、WS token，并删除 `uploads/exports/workspace` 下对应用户与会话目录。
- 删除顺序按外键依赖从子到父；不能只依赖 SQLite 级联。
- 所有查询必须带 `user_id` 归属校验。

### 5.3 消息模块

职责：消息入库、历史消息查询、消息顺序控制。

接口：
- `GET /api/chat/ls/{conversation_id}`：响应 `message_id`、`role`、`content`、`attachments`、`created_at`。
- WebSocket 接收用户消息后写入数据库，并触发一次分析任务。

数据表：`messages`。

关键约束：
- `role`：`user`、`assistant`、`tool`、`system`。
- `message_type` 区分普通文本、工具调用、系统提示。
- `seq_no` 在会话内单调递增，历史回放按 `seq_no` 排序。
- 工具调用写入 `messages`（`role=tool`、`tool_name`、`tool_status`），同时追加 `task_logs`。
- 一条用户消息对应一次分析任务。

### 5.4 附件模块

职责：文件保存、删除、下载、路径校验。

接口：
- `POST /api/attachment/upload`：请求 `conversation_id` 与文件对象，响应 `attachment_id`、`file_name`、`file_path`。
- `POST /api/attachment/delete`：请求 `attachment_id`。
- `GET /api/attachment/ls`：按 `conversation_id` 列出附件。
- `GET /api/attachment/get`：请求 `attachment_id`，返回文件流或下载信息。

数据表：`attachments`。

关键约束：
- 附件存储到 `storage/uploads/{user_id}/{conversation_id}/`。
- 数据库只存相对路径；读写前用 `safe_path` 校验解析后的路径仍在根目录内。
- 保留中文文件名；文件大小受 `UPLOAD_MAX_MB` 限制。
- `parse_status` 记录解析状态，解析流程在附件模块内扩展。

### 5.5 长连接模块

职责：会话级实时连接、连接鉴权、消息推送、连接关闭。

接口：
- `POST /api/chat/ws-token`：请求 `conversation_id`，响应 `websocket_token`、`expires_in`。
- `WS /api/chat/ws/chat`：连接参数 `websocket_token`、`conversation_id`。

数据表：`websocket_tokens`。

关键约束：
- 一次性 token，有效期 60 秒；连接成功后写 `consumed_at`。
- 必须校验 token 有效期、会话归属、用户身份。
- `ConnectionManager` 维护 `{conversation_id: set[WebSocket]}`，负责注册、注销、广播。
- `EventPublisher` 协议隔离 harness 与 WebSocket；harness 只能依赖协议。
- 连接关闭时从管理器移除；断线重连由前端重新申请 token。

### 5.6 任务模块

职责：分析任务创建、状态流转、取消执行、日志记录、临时令牌签发。

接口：
- `GET /api/tasks/{task_id}`：响应 `task_status`、`current_step`、`started_at`、`finished_at`、`error_message`。
- `GET /api/tasks?conversation_id=`：按会话返回任务摘要，含 `result_id`。
- `GET /api/tasks/{task_id}/logs`：返回任务工具日志。
- `POST /api/tasks/{task_id}/cancel`：取消当前任务。
- 任务由用户消息触发，不单独暴露创建接口。

数据表：`analysis_tasks`、`task_logs`。

关键约束：
- 状态：`queued`、`running`、`success`、`failed`、`cancelled`。
- 同一会话同一时间只允许一个 `running` 任务；应用层检查 + SQLite 部分唯一索引。
- 任务在进程内通过 `asyncio.create_task` 执行；启动时把遗留 `running` 标记为 `failed`。
- `analysis/coordinator.py` 是唯一修改 `task_status` 的入口。
- 取消任务时设置 `cancelled`，停止后续步骤并发送 `done`。
- 分析成功后，Coordinator 将结论写入 `messages`（`role=assistant`、`message_type=analysis`），刷新历史不会丢失回答。
- `analysis/service.py` 只提供任务与结果的 CRUD，不承载状态机。

### 5.7 分析模块

职责：拼装上下文、执行查询和文件工具、生成结构化结论。

组成：
- `agent/factory.py`：懒加载 `ChatDeepSeek`，用 `create_agent` 组装模型、工具、`ToolStrategy(AnalysisOutput)` 与工具调用上限中间件。
- `agent/prompt.py`：六段式输出系统提示词。
- `agent/output.py`：`AnalysisOutput`、`KeyMetric`、`Evidence`。
- `harness/runtime.py`：`AgentRuntimeContext`（`user_id`、`conversation_id`、`task_id`）与执行状态。
- `harness/context.py`：历史消息、`context_summaries`、附件文本按预算组装。
- `harness/executor.py`：`astream` 调用、token 事件、工具事件、校验重试、用量汇总。
- `harness/validator.py`：六段式结构校验 + 证据可追溯；失败生成纠正消息，最多 2 次。
- `harness/tools.py`：`ToolExecutor` 唯一工具入口；SQL 查询与 FTS5 文本检索。

关键约束：
- 工具调用必须经过 `ToolExecutor`：参数校验、超时、写 `messages`/`task_logs`、发事件都在这层完成。
- SQL 工具只读连接 `business.db`；表白名单、强制 `LIMIT`、查询超时；禁止 DDL、DML、多语句。
- 文本检索使用 FTS5，数据源为附件解析文本与业务库文本字段；返回字段可直接映射到证据列表。
- 证据中的 `source_name`、`related_metric` 必须能对应到已成功执行的工具结果。
- 无 DeepSeek Key 时服务仍可启动，分析任务返回明确错误。
- OpenCode Zen 接入：base URL 使用 `https://opencode.ai/zen/go/v1`，请求头带 `x-opencode-session`，并传 `thinking={"type":"disabled"}`；否则 thinking 模式不支持强制 `tool_choice`。

执行流：

```
用户消息
  → 消息模块写入数据库
  → 任务模块创建 analysis_tasks(queued)
  → coordinator 置 running，发 task_status
  → harness/context 组装上下文
  → harness/executor 调用 agent.astream
      → token → message_delta
      → 工具 → harness/tools → tool_start / tool_finish
  → harness/validator 校验（失败最多纠错 2 次）
  → 结果模块写入 analysis_results
  → result_ready → done
  → 异常：failed → error → done
```

### 5.8 结果模块

职责：分析结果落库、结果导出、结果文件管理、上下文摘要压缩。

接口：
- `GET /api/results/{task_id}`：响应 `problem_definition`、`key_metrics`、`evidence_list`、`conclusion_text`、`missing_data_text`、`next_action_text`。
- `GET /api/results/{task_id}/file`：下载 Markdown 结果文件。

数据表：`analysis_results`、`context_summaries`。

关键约束：
- 结果必须完整保存六段式字段与 `result_markdown`、`result_file_path`。
- 导出文件写入 `storage/exports/{user_id}/{conversation_id}/`，数据库只存相对路径。
- 上下文压缩按 `start_seq_no`、`end_seq_no` 生成摘要，供后续轮次复用。
- 结果查询必须校验任务归属当前用户。
- `ResultResponse` 的 `key_metrics`、`evidence_list` 使用 `KeyMetric`、`Evidence` 强类型，不再使用裸 `list[dict]`。

### 5.9 配置模块

职责：系统配置读取和热更新。

接口：
- `POST /api/admin/reload`：响应 `status`、`message`。
- `GET /api/admin/configs`：查看系统配置。
- `GET /api/admin/logs`：查看任务日志，支持 `task_id`、`log_level`、`limit` 过滤。

数据表：`system_configs`。

关键约束：
- `core/config.py` 使用 pydantic-settings 与环境变量；`get_settings()` 带缓存。
- 重载时清理设置缓存并重新读取 `system_configs`。
- 数据库连接串变更需要重启进程，重载接口只处理可热更新项。
- 管理端接口仅允许 `role=admin` 的用户访问。

## 6. 数据模型

| 表 | 字段 |
|---|---|
| `users` | `id`、`external_user_id`、`username`、`display_name`、`role`、`status`、`created_at`、`updated_at` |
| `conversations` | `id`、`user_id`、`title`、`status`、`last_message_at`、`created_at`、`updated_at` |
| `messages` | `id`、`conversation_id`、`role`、`message_type`、`content`、`tool_name`、`tool_status`、`seq_no`、`created_at` |
| `attachments` | `id`、`conversation_id`、`message_id`、`file_name`、`file_path`、`file_type`、`file_size`、`parse_status`、`created_at` |
| `analysis_tasks` | `id`、`conversation_id`、`user_id`、`input_text`、`task_status`、`current_step`、`started_at`、`finished_at`、`error_message` |
| `analysis_results` | `id`、`task_id`、`conversation_id`、`problem_definition`、`key_metrics_json`、`evidence_list_json`、`conclusion_text`、`missing_data_text`、`next_action_text`、`result_markdown`、`result_file_path`、`created_at` |
| `context_summaries` | `id`、`conversation_id`、`start_seq_no`、`end_seq_no`、`summary_text`、`created_at` |
| `websocket_tokens` | `id`、`user_id`、`conversation_id`、`token`、`expires_at`、`consumed_at`、`created_at` |
| `system_configs` | `id`、`config_key`、`config_value`、`config_group`、`updated_at` |
| `task_logs` | `id`、`task_id`、`log_level`、`log_type`、`log_content`、`created_at` |

主键约定：
- 业务表使用带前缀字符串：`conv_`、`msg_`、`task_`、`att_`、`res_`、`sum_`、`wst_`。
- `messages.id` 与 `task_logs.id` 使用自增整数。
- 时间统一 UTC。

## 7. 接口总览

| 方法 | 路径 | 所属模块 |
|---|---|---|
| GET | `/auth/login` | 认证接入 |
| GET | `/auth/callback` | 认证接入 |
| GET | `/api/me` | 认证接入 |
| POST | `/api/chat/create` | 会话 |
| POST | `/api/chat/delete` | 会话 |
| POST | `/api/chat/update` | 会话 |
| GET | `/api/chat/ls` | 会话 |
| GET | `/api/chat/ls/{conversation_id}` | 消息 |
| POST | `/api/attachment/upload` | 附件 |
| POST | `/api/attachment/delete` | 附件 |
| GET | `/api/attachment/ls` | 附件 |
| GET | `/api/attachment/get` | 附件 |
| POST | `/api/chat/ws-token` | 长连接 |
| WS | `/api/chat/ws/chat` | 长连接 |
| GET | `/api/tasks/{task_id}` | 任务 |
| GET | `/api/tasks?conversation_id=` | 任务 |
| GET | `/api/tasks/{task_id}/logs` | 任务 |
| POST | `/api/tasks/{task_id}/cancel` | 任务 |
| GET | `/api/results/{task_id}` | 结果 |
| GET | `/api/results/{task_id}/file` | 结果 |
| POST | `/api/admin/reload` | 配置 |
| GET | `/api/admin/configs` | 配置 |
| GET | `/api/admin/logs` | 配置 |

## 8. 实时事件

| 事件 | 字段 |
|---|---|
| `message_start` | `task_id`、`conversation_id` |
| `message_delta` | `task_id`、`delta_text` |
| `tool_start` | `task_id`、`tool_name` |
| `tool_finish` | `task_id`、`tool_name`、`tool_result_summary` |
| `task_status` | `task_id`、`task_status`、`current_step` |
| `result_ready` | `task_id`、`result_id` |
| `error` | `task_id`、`error_message` |
| `done` | `task_id`、`finished_at` |

## 9. 文件存储

- 附件：`storage/uploads/{user_id}/{conversation_id}/`
- 导出：`storage/exports/{user_id}/{conversation_id}/`
- 临时文件：`storage/workspace/{user_id}/{conversation_id}/`
- 数据库只存相对路径。
- 删除会话时同时删除三类目录。
- 所有读写路径必须经过根目录包含校验。
- `business.db` 由 `scripts/seed_demo.py` 生成，包含商品目录优化与客户行为分析两个示例场景；SQL 工具白名单见项目根 `.env.example` 的 `SQL_ALLOWED_TABLES`。

## 10. 编码约定

- 路由层只负责参数绑定、鉴权与调用 Service，不写业务逻辑。
- 数据访问统一走 Repository；Service 负责业务规则；Coordinator 负责任务状态机。
- 异步 SQLAlchemy，session 使用 `expire_on_commit=False`。
- SQLite 连接启用 WAL、`busy_timeout`、`foreign_keys`。
- 不在 import 阶段初始化 DeepSeek 客户端。
- harness 不直接 import WebSocket；只依赖 `EventPublisher`。
- 工具执行只通过 `ToolExecutor`，工具函数保持纯粹。
- 所有用户输入的查询、文件路径、会话 ID 都要做归属与边界校验。
- 环境变量统一维护在项目根 `.env.example`，后端与前端共用根 `.env`；不要提交 `.env`。
- `PRD.md` 为 GBK 编码，只读，不修改。

## 11. 后端实施顺序

1. `core/config.py` → `core/database.py` → `core/models.py` → `scripts/init_db.py`
2. 认证接入模块：`auth/adapter.py` → `auth/service.py` → `auth/router.py`
3. 会话模块与消息模块：`workspace/schemas.py` → `workspace/repository.py` → `workspace/service.py` → `workspace/router.py`
4. 附件模块：`workspace/storage.py` → 上传/删除/下载接口
5. 长连接模块：`core/realtime.py` → `core/events.py` → `ws-token` → WS 路由
6. 任务模块：`analysis/service.py` → `analysis/coordinator.py` → `analysis/router.py`
7. 分析模块：`harness/runtime.py` → `harness/context.py` → `harness/tools.py` → `harness/executor.py` → `agent/prompt.py` → `agent/output.py` → `agent/factory.py`
8. 校验与结果模块：`harness/validator.py` → 结果落库 → 导出 → 上下文摘要
9. 配置模块：`admin/service.py` → `admin/router.py`
10. 示例数据与完整演示链路：`scripts/seed_demo.py`

## 12. 验证方式

> 完整的安装、启动、停止、访问地址与常见问题见项目根目录 [README.md](README.md)。

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

- `/health` 返回服务状态。
- `/docs` 可见全部接口。
- 授权登录 → 工作台 → 创建会话 → 上传附件 → 发送消息。
- WebSocket 能看到 `message_start`、`message_delta`、`tool_start`、`tool_finish`、`result_ready`、`done`。
- 结果区返回六段式结构。
- 结果文件可导出并重新下载。
- `POST /api/admin/reload` 后配置即时生效。
- `uv run pytest` 通过。

## 13. 前端

- 技术栈：Vue 3 + Vite + Vue Router；入口 `frontend/`。
- 页面：`LoginPage`、`CallbackPage`、`WorkspacePage`、`AdminPage`。
- 工作台：三栏布局（会话 / 对话 / 结果-任务-附件 Tab），支持会话 CRUD、历史消息、WebSocket 实时事件、附件上传下载、六段式结果与 Markdown 导出。
- 管理端：配置、日志、数据源、功能开关四个 Tab；数据源/开关按 `system_configs.config_group` 过滤。
- API 封装：`frontend/src/api/`；实时连接：`frontend/src/composables/useRealtime.js`。
- 环境变量：项目根 `.env` 中的 `VITE_API_BASE_URL`、`VITE_WS_BASE_URL`；Vite `envDir` 指向根目录。
- 安全：根 `.env` 同时包含后端密钥与 `VITE_` 变量；Vite 只暴露 `VITE_` 前缀，后端 Key 不会进入前端包。
- 启动：`cd frontend; npm install; npm run dev`（默认 5173）；完整启动/停止说明见根目录 [README.md](README.md)。
- Demo 管理员：登录页“管理员登录”调用 `/auth/login?as_admin=true`。
- 当前状态：构建、启动、CORS 与接口联调通过；浏览器逐页交互待手动验收，详见 `docs/acceptance/M11-frontend.md`。
