# 经营归因分析系统

围绕业务问题持续追问，调用数据工具补充证据，生成可追溯的六段式归因结论。

## 技术栈

- 后端：Python 3.12、FastAPI、SQLAlchemy 2.x、SQLite、LangChain、OpenCode Zen
- 前端：Vue 3、Vue Router、Vite
- 配置：项目根目录 `.env`，后端与前端共用

## 目录

```
backend/          后端服务、数据库、分析 Agent
frontend/         前端页面
docs/             页面接口文档、验收报告、Pen 设计
CLAUDE.md         后端架构与编码约定
项目规划.md       模块拆分、里程碑与验收流程
```

## 前置条件

- Python 3.12
- `uv`
- Node.js 20+
- Windows PowerShell

## 首次安装

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
uv sync

cd "C:\AIcoding\Business Attribution System\frontend"
npm install
```

## 配置

- 项目根目录 `.env` 是唯一实际配置，后端与前端都读取它。
- 修改模型 Key、base URL、模型名时，只改根目录 `.env`。
- `.env` 不入库；`.env.example` 是模板。
- 如果根目录没有 `.env`，启动脚本会自动从 `.env.example` 复制一份。

## 启动服务

### 方式一：后台脚本（推荐）

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
.\start.ps1 -SkipInstall

cd "C:\AIcoding\Business Attribution System\frontend"
.\start.ps1 -SkipInstall
```

- 第一次运行可以去掉 `-SkipInstall`，让脚本安装依赖。
- 脚本在后台启动服务，PID 写入 `.runtime/`，日志写入 `logs/`。

### 方式二：前台运行（方便看日志）

```powershell
# 终端 1：后端
cd "C:\AIcoding\Business Attribution System\backend"
uv run uvicorn app.main:app --reload --port 8000

# 终端 2：前端
cd "C:\AIcoding\Business Attribution System\frontend"
npm run dev
```

## 访问页面

- 前端工作台：<http://127.0.0.1:5173>
- 登录页：<http://127.0.0.1:5173/login>
- 后端健康检查：<http://127.0.0.1:8000/health>
- 后端接口文档：<http://127.0.0.1:8000/docs>

不要直接双击 `frontend/index.html`，必须通过 `5173` 地址访问，否则无法连接后端。

## 停止服务

```powershell
cd "C:\AIcoding\Business Attribution System\frontend"
.\stop.ps1

cd "C:\AIcoding\Business Attribution System\backend"
.\stop.ps1
```

- 如果提示 `already running`，先执行对应的 `stop.ps1`，再重新 `start.ps1`。
- 前台运行时直接按 `Ctrl+C`。

## 测试与契约检查

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
uv run pytest -q
uv run ruff check app tests scripts
uv run python -m scripts.check_page_contract
```

页面接口文档：

- 事实源：`docs/page-interface.yaml`
- 生成 Markdown：`uv run python -m scripts.render_page_interface`
- 生成结果：`docs/page-interface.md`

## 示例数据

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
uv run python -m scripts.seed_demo
uv run python -m scripts.seed_configs
```

- `seed_demo.py`：商品目录优化、客户行为分析两个业务场景。
- `seed_configs.py`：管理端数据源与功能开关演示配置。

## 常见问题

- **接口失败或登录不了**：先打开 <http://127.0.0.1:8000/health>，确认后端已启动。
- **前端页面空白**：确认前端 `npm run dev` 或 `start.ps1` 已运行，并访问 `5173`。
- **端口被占用**：执行
  ```powershell
  Get-NetTCPConnection -LocalPort 8000,5173 -State Listen
  ```
- **日志位置**：
  - 后端：`backend/logs/backend.out.log`、`backend/logs/backend.err.log`
  - 前端：`frontend/logs/frontend.out.log`、`frontend/logs/frontend.err.log`

## 文档索引

- [CLAUDE.md](CLAUDE.md)：后端架构、接口、编码约定
- [项目规划.md](项目规划.md)：模块拆分、里程碑、验收流程
- [docs/DELIVERY.md](docs/DELIVERY.md)：演示版交付说明与演示脚本
- [docs/page-interface.md](docs/page-interface.md)：页面接口对照
- [docs/acceptance/](docs/acceptance/)：各模块与真实链路验收报告
- [docs/design/attribution-ui.pen](docs/design/attribution-ui.pen)：Pen UI 设计
