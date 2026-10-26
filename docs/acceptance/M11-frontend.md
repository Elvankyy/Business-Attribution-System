# M11 前端联调 验收报告

- 验收日期：2026-10-24
- 环境：Node 24.21.0、npm 11.19.0、Vue 3.5、Vue Router 4.5、Vite 8.3.5
- 关联需求：PRD 2.1.3 页面需求、2.1.5 前端模块要求、2.1.13 完整演示链路
- 交付物：
  - `frontend/package.json`、`vite.config.js`、`index.html`
  - 项目根 `.env.example`（统一配置，含后端与前端变量）
  - `frontend/src/router/index.js`
  - `frontend/src/api/`（client、auth、workspace、analysis、admin）
  - `frontend/src/composables/`（useAuth、useWorkspace、useRealtime）
  - `frontend/src/pages/`（LoginPage、CallbackPage、WorkspacePage、AdminPage）
  - `frontend/src/components/`（AppHeader、ConversationList、ChatPanel、MessageItem、MessageInput、AttachmentSidebar、TaskStatusPanel、ResultPanel、ResultSection）
  - `frontend/src/styles/`（variables.css、base.css）
  - `frontend/start.ps1`、`frontend/stop.ps1`

## 已实现功能

- **登录入口**：分析用户登录、管理员登录；管理员登录走 `/auth/login?as_admin=true`。
- **回调页**：解析 `#token=`，保存 JWT，调用 `/api/me` 校验后跳转工作台。
- **路由守卫**：未登录跳 `/login`，已登录访问 `/login` 跳工作台。
- **聊天工作台**：三栏布局；会话创建、切换、重命名、删除；历史消息加载。
- **实时链路**：申请 ws-token、建立 WebSocket、指数退避重连；处理 `message_start`、`message_delta`、`tool_start`、`tool_finish`、`task_status`、`result_ready`、`error`、`done`。
- **消息区**：用户/助手/工具消息渲染；助手内容 Markdown + DOMPurify；附件消息可下载；流式文本占位。
- **输入区**：Enter 发送、Shift+Enter 换行；运行中显示“停止分析”。
- **附件侧栏**：上传、列表、下载、删除；调用新增的 `GET /api/attachment/ls`。
- **任务面板**：状态、当前步骤、开始/结束时间、错误、工具执行时间线。
- **结果面板**：六段式展示；复制全部；导出 Markdown 文件。
- **管理端**：配置、日志、数据源、功能开关四个 Tab；数据源/开关按 `system_configs.config_group` 过滤。

## 构建与联调检查

| 检查项 | 结果 |
|---|---|
| `npm install` | 40 个包，0 个漏洞 |
| `npm run build` | 成功，50 个模块，JS 193.59 KB，CSS 12.22 KB |
| 后端 `/health` | `status=ok`，`llm_configured=true` |
| 前端 `/` | 200 |
| 前端 `/src/main.js` | 200 |
| CORS 预检（Origin 5173） | 200，`Access-Control-Allow-Origin: http://127.0.0.1:5173` |
| 后端真实 E2E | 见 [E2E-01](E2E-01-product-catalog.md)、[E2E-02](E2E-02-customer-behavior.md) |

## 验收标准核对

- [x] 四个页面代码可构建、路由可注册。
- [x] 前端可启动并返回页面与模块脚本。
- [x] 后端 CORS 允许 5173 来源。
- [x] 前端已接入会话、消息、附件、任务、结果、管理端接口。
- [x] 管理端有配置/日志/数据源/功能开关四个 Tab。
- [x] 按演示标准确认核心页面与链路可用（登录、发消息、实时事件、上传附件、结果导出、管理端）。
- [ ] 移动端导航（当前 <640px 隐藏会话列表，未提供移动端菜单）。

## 问题与修复

1. **附件列表接口缺失**：前端附件侧栏需要按会话列出附件，已补 `GET /api/attachment/ls` 并加测试。
2. **管理员演示入口缺失**：Demo 认证中心默认返回分析用户，已支持 `/auth/login?as_admin=true` 登录管理员。
3. **统一 `.env`**：项目根 `.env` 同时提供后端配置与前端 `VITE_` 变量，默认指向 `127.0.0.1:8000` 与 `ws://127.0.0.1:8000`。
4. **后端契约补强**：助手回答落库、历史任务/日志接口、结果强类型、配置种子与页面接口 YAML/契约检查已完成，见 [M11.1](M11.1-contract-support.md)。

## 遗留项

- **浏览器交互验收**：当前环境没有浏览器自动化工具，未做真实点击/视觉验收；需要手动打开 `http://127.0.0.1:5173` 完成最后一轮确认。
- 历史结果：按会话保存最后一个 `task_id` 到 localStorage，刷新后可恢复；后端暂无“按会话列出任务/结果”的接口。
- 模型走工具调用路径时没有 `message_delta` 文本流；工具事件和最终结果仍完整展示。
- 移动端仅做基础响应式，会话列表在小屏隐藏，未实现抽屉菜单。
- 会话重命名/删除使用 `window.prompt/confirm`，交互较基础。
- 数据源与功能开关目前是配置分组视图，未提供独立的新增/编辑表单。

## 结论

通过（演示标准）：构建、启动、CORS、接口联调完成，核心链路可用，项目按演示标准收尾。
