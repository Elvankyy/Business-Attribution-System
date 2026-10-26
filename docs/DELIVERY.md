# 经营归因分析系统 — 演示版交付说明

## 交付状态

按**课程/演示标准**收尾。

- 后端 M00–M10、M11.1 已验收。
- 前端 M11、M11.2、M11.3 已验收（演示标准）。
- 后端：83 tests passed，ruff 全通过。
- 前端：`npm run build` 成功，53 个模块。
- 页面接口契约：23 个动作，0 个缺失。
- 真实模型链路：E2E-01 商品目录优化、E2E-02 客户行为分析均 `success`。

## 交付物

| 内容 | 路径 |
|---|---|
| 项目启动说明 | [README.md](../README.md) |
| 后端架构与编码约定 | [CLAUDE.md](../CLAUDE.md) |
| 模块规划与进度 | [项目规划.md](../项目规划.md) |
| 页面接口对照 | [page-interface.md](page-interface.md) |
| 各模块验收报告 | [acceptance/](acceptance/) |
| Pen UI 设计 | [design/attribution-ui.pen](design/attribution-ui.pen) |
| 后端代码 | `backend/` |
| 前端代码 | `frontend/` |

## 启动

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
.\start.ps1 -SkipInstall

cd "C:\AIcoding\Business Attribution System\frontend"
.\start.ps1 -SkipInstall
```

访问：

- 前端：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8000/health>
- 接口文档：<http://127.0.0.1:8000/docs>

## 演示脚本

### 1. 登录

打开 <http://127.0.0.1:5173/login>，点击“登录”。Demo 认证中心会自动完成授权并进入工作台。

### 2. 场景一：商品目录优化

1. 新建会话，标题可写“无线耳机销量下降分析”。
2. 输入：`为什么无线耳机最近销量下降？`
3. 切到右侧“任务”Tab，观察工具执行过程。
4. 完成后切到“结果”Tab，查看六段式结果，点击“导出文件”。

预期结论：

- 9 月订单 34 单，8 月 45 单，下降约 24.4%。
- 搜索曝光下降 32.3%，点击下降 38.7%。
- 点击到下单的转化率由 14.5% 升至 17.9%。
- 主要原因是流量端收缩，而非转化或定价恶化。

### 3. 场景二：客户行为分析

1. 新建会话，标题可写“客户流失风险排查”。
2. 输入：`哪些客户有流失风险，原因是什么？`
3. 查看结果并导出。

预期结论：

- 客户C 风险最高：唯一订单被取消，9 天无访问，0 次加购。
- 客户E 次要风险：499 元订单退款后无复访。
- 客户B 潜在风险：加购 2 件仅成交 1 件。
- 客户A、D 当前无流失信号。

### 4. 历史任务与继续追问

- 右侧“历史任务”下拉可以切换同一会话的历史轮次。
- 切换后会加载对应任务状态、工具日志和六段式结果。
- 可以在输入框中继续追问。

### 5. 附件

- 切到“附件”Tab，上传文件。
- 支持下载、删除，列表显示文件名、类型、大小和解析状态。

### 6. 管理端

1. 退出当前登录。
2. 在登录页点击“管理员登录”。
3. 打开 <http://127.0.0.1:5173/admin>。
4. 查看五个 Tab：配置、日志、任务记录、数据源、功能开关。
5. 点击“重载配置”验证配置即时生效。

## 最终验证命令

```powershell
cd "C:\AIcoding\Business Attribution System\backend"
uv run pytest -q
uv run ruff check app tests scripts
uv run python -m scripts.check_page_contract

cd "C:\AIcoding\Business Attribution System\frontend"
npm run build
```

## 已知限制（演示版）

- 认证为 Demo 模式，没有真实密码/认证中心；`as_admin=true` 是演示入口，不能公网暴露。
- 附件文本解析尚未实现，文本检索目前基于 `documents_fts`。
- 工具调用路径没有 `message_delta` 自然语言文本流，只有工具事件和最终结果。
- FTS5 多关键词为 AND 语义，部分自然语言查询召回有限。
- 上下文摘要为截断拼接，不是模型摘要。
- 没有前端自动化测试、浏览器回归测试和移动端抽屉导航。
- 没有生产部署、HTTPS、监控、限流和备份方案。

## 后续如需上线

1. 接入真实 OAuth/OIDC 认证中心，移除 Demo 管理员入口。
2. 实现附件解析（PDF/Excel/文本）并接入检索。
3. 补 `message_delta` 文本流与前端流式渲染。
4. 生产部署、HTTPS、日志监控、限流与备份。
5. 增加前端自动化测试和浏览器回归测试。
