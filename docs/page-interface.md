# 页面接口文档

> 本文件由 `docs/page-interface.yaml` 生成，请修改 YAML 后重新运行 `python -m scripts.render_page_interface`。

- 项目：经营归因分析系统
- 生成日期：2026-10-24

## 状态说明

- 事实来源：后端 OpenAPI 与前端 src/api 实际调用
- status: matched=前后端一致；extension=实现新增（PRD 未列）；frontend_pending=后端已就绪、前端待接入；missing=后端缺失

## 概览

- 页面数：4
- 动作数：29
- 实现新增：10
- 一致：19

## 授权登录入口页

- 路由：`/login`
- 组件：`frontend/src/pages/LoginPage.vue`

| 动作 | 类型 | 接口 | 请求 | 响应 | 错误 | 状态 |
|---|---|---|---|---|---|---|
| 登录 | redirect | `GET /auth/login` | — | 302 到认证中心 | — | 一致 |
| 管理员登录 | redirect | `GET /auth/login` | as_admin=true | 302，state 包含 admin 角色 | — | 实现新增 |

## 登录回调页

- 路由：`/auth/callback`
- 组件：`frontend/src/pages/CallbackPage.vue`

| 动作 | 类型 | 接口 | 请求 | 响应 | 错误 | 状态 |
|---|---|---|---|---|---|---|
| 校验登录态 | rest | `GET /api/me` | — | id、external_user_id、username、display_name、role、status | 401 | 实现新增 |

## 聊天工作台页

- 路由：`/workspace/:conversationId?`
- 组件：`frontend/src/pages/WorkspacePage.vue`

| 动作 | 类型 | 接口 | 请求 | 响应 | 错误 | 状态 |
|---|---|---|---|---|---|---|
| 加载会话列表 | rest | `GET /api/chat/ls` | — | conversation_id、title、status、last_message_at | 401 | 一致 |
| 新建会话 | rest | `POST /api/chat/create` | title=string | conversation_id、title、status | 401、422 | 一致 |
| 加载历史消息 | rest | `GET /api/chat/ls/{conversation_id}` | conversation_id=path | message_id、role、message_type、content、tool_name、tool_status、attachments、created_at | 401、404 | 一致 |
| 加载附件列表 | rest | `GET /api/attachment/ls` | conversation_id=query | attachment_id、file_name、file_type、file_size、parse_status、created_at | 401、404 | 实现新增 |
| 重命名会话 | rest | `POST /api/chat/update` | conversation_id=string、title=string | conversation_id、title、status | 401、404 | 一致 |
| 删除会话 | rest | `POST /api/chat/delete` | conversation_ids=string[] | deleted | 401 | 一致 |
| 申请 WebSocket token | rest | `POST /api/chat/ws-token` | conversation_id=string | websocket_token、expires_in | 401、404 | 一致 |
| 建立实时连接 | websocket | — | websocket_token=query、conversation_id=query | connected 事件、8 种分析事件 | 1008 策略关闭 | 一致 |
| 发送分析问题 | websocket_message | — | type=user_message、content=string | message_start、task_status、tool_start、tool_finish、message_delta、result_ready、error、done | 已有运行中任务 | 一致 |
| 停止分析 | rest | `POST /api/tasks/{task_id}/cancel` | task_id=path | task_id、task_status、current_step、started_at、finished_at、error_message | 401、404 | 实现新增 |
| 刷新恢复任务状态 | rest | `GET /api/tasks/{task_id}` | task_id=path | task_id、task_status、current_step、started_at、finished_at、error_message | 401、404 | 一致 |
| 历史任务列表 | rest | `GET /api/tasks` | conversation_id=query | task_id、task_status、current_step、input_text、started_at、finished_at、error_message、result_id | 401、404 | 实现新增 |
| 历史任务日志 | rest | `GET /api/tasks/{task_id}/logs` | task_id=path | log_level、log_type、log_content、created_at | 401、404 | 实现新增 |
| 查看分析结果 | rest | `GET /api/results/{task_id}` | task_id=path | problem_definition、key_metrics、evidence_list、conclusion_text、missing_data_text、next_action_text | 401、404 | 一致 |
| 下载结果文件 | rest | `GET /api/results/{task_id}/file` | task_id=path | Markdown 文件流 | 401、404 | 实现新增 |
| 上传附件 | rest | `POST /api/attachment/upload` | conversation_id=form、file=file | attachment_id、file_name、file_path | 400 文件过大、401、404 | 一致 |
| 删除附件 | rest | `POST /api/attachment/delete` | attachment_id=string | deleted | 401、404 | 一致 |
| 下载附件 | rest | `GET /api/attachment/get` | attachment_id=query | 文件流、content-disposition | 401、404 | 一致 |
| 复制全部结果 | frontend | — | — | — | — | 一致 |
| 退出登录 | frontend | — | — | — | — | 一致 |

## 系统管理页

- 路由：`/admin`
- 组件：`frontend/src/pages/AdminPage.vue`

| 动作 | 类型 | 接口 | 请求 | 响应 | 错误 | 状态 |
|---|---|---|---|---|---|---|
| 加载系统配置 | rest | `GET /api/admin/configs` | — | config_key、config_value、config_group、updated_at | 401、403 | 实现新增 |
| 加载任务日志 | rest | `GET /api/admin/logs` | limit=query、task_id=optional query | task_id、log_level、log_type、log_content、created_at | 401、403 | 实现新增 |
| 加载任务记录 | rest | `GET /api/admin/tasks` | limit=query | task_id、conversation_id、conversation_title、user_id、username、display_name、task_status、current_step、input_text、started_at、finished_at、error_message、result_id | 401、403 | 实现新增 |
| 重载系统配置 | rest | `POST /api/admin/reload` | — | status、message | 401、403 | 一致 |
| 数据源 Tab | frontend | — | — | 按 config_group=data_source 本地过滤 | — | 一致 |
| 功能开关 Tab | frontend | — | — | 按 config_group=feature 本地过滤 | — | 一致 |

## WebSocket

- 端点：`/api/chat/ws/chat`

### 服务端事件

| 事件 | 字段 | 消费方 | 状态 |
|---|---|---|---|
| message_start | task_id、conversation_id | WorkspacePage | 一致 |
| message_delta | task_id、delta_text | WorkspacePage | 一致 |
| tool_start | task_id、tool_name | WorkspacePage | 一致 |
| tool_finish | task_id、tool_name、tool_result_summary | WorkspacePage | 一致 |
| task_status | task_id、task_status、current_step | WorkspacePage | 一致 |
| result_ready | task_id、result_id | WorkspacePage | 一致 |
| error | task_id、error_message | WorkspacePage | 一致 |
| done | task_id、finished_at | WorkspacePage | 一致 |
| connected | conversation_id | 未处理 | 实现新增 |
| pong | — | 未处理 | 实现新增 |

### 客户端消息

| 消息 | 字段 | 生产方 | 状态 |
|---|---|---|---|
| user_message | content | WorkspacePage | 一致 |
| cancel | task_id | 未使用（前端走 REST cancel） | 实现新增 |
| ping | — | 未使用 | 实现新增 |

## 后端补充

| 事项 | 说明 | 状态 |
|---|---|---|
| assistant-persistence | 分析成功后保存 role=assistant、message_type=analysis 的结论消息，刷新历史不会再丢失回答 | 一致 |
| task-list | GET /api/tasks?conversation_id= 返回任务摘要与 result_id | 一致 |
| task-logs | GET /api/tasks/{task_id}/logs 返回工具执行日志 | 一致 |
| result-schema | ResultResponse.key_metrics/evidence_list 已改为强类型 KeyMetric/Evidence | 一致 |
| config-seed | scripts/seed_configs.py 写入 data_source/feature 演示配置 | 一致 |
| admin-tasks | GET /api/admin/tasks 返回跨会话任务记录（会话、用户、状态、输入、result_id） | 一致 |

## 前端待办

- [ ] 浏览器逐页验收：登录、工作台、历史任务、管理端
