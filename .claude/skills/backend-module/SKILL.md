---
name: backend-module
description: Implement and verify one backend module (M00–M11) of the 经营归因分析系统. Use whenever the user says to start or continue a backend module, implement a module, run module tests, or generate an acceptance report. Always read CLAUDE.md and 项目规划.md first.
---

# 后端模块开发流程

## 开始前必读

1. `CLAUDE.md`：技术栈、目录结构、九个后端模块、接口契约、编码约定。
2. `项目规划.md`：M00–M11 模块、前置依赖、测试项、验收标准、验收报告模板。

## 模块地图

| 编号 | 模块 | 前置依赖 | 验收报告 |
|---|---|---|---|
| M00 | 基础设施 | 无 | `docs/acceptance/M00-infrastructure.md` |
| M01 | 认证接入 | M00 | `docs/acceptance/M01-auth.md` |
| M02 | 会话 | M00、M01 | `docs/acceptance/M02-conversation.md` |
| M03 | 消息 | M02 | `docs/acceptance/M03-message.md` |
| M04 | 附件 | M02 | `docs/acceptance/M04-attachment.md` |
| M05 | 长连接 | M01、M02 | `docs/acceptance/M05-realtime.md` |
| M06 | 任务 | M03、M05 | `docs/acceptance/M06-task.md` |
| M07 | 分析 | M06 | `docs/acceptance/M07-analysis.md` |
| M08 | 结果 | M07 | `docs/acceptance/M08-result.md` |
| M09 | 配置 | M00 | `docs/acceptance/M09-config.md` |
| M10 | 示例数据 | M00、M07、M08 | `docs/acceptance/M10-demo-data.md` |
| M11 | 前端联调 | 后端接口稳定 | `docs/acceptance/M11-frontend.md` |

## 工作流程

1. 确认当前模块及其前置依赖。若前置模块尚未“已验收”，停止并向用户说明阻塞原因。
2. 阅读 `项目规划.md` 中该模块的详情，复述目标、范围、文件落点、接口、测试项与验收标准。
3. 只在该模块的文件范围内实现；跨模块调用必须通过 Service 接口，不直接引用其他模块的 router 或 repository。
4. 同步编写或更新测试，优先使用测试替身：临时 SQLite、`FakeEventPublisher`、`FakeLLM`、`FakeTool`。
5. 运行该模块的测试：`cd backend && uv run pytest tests/<module>`，并执行模块清单中的手工/API 验证。
6. 从 `docs/acceptance/TEMPLATE.md` 复制生成 `docs/acceptance/MXX-<module>.md`，填写真实验收结果。
7. 更新 `项目规划.md` 的进度表：未开始 → 进行中 → 待验收 → 已验收。
8. 只有当前模块“已验收”后，才进入依赖它的下一个模块。

## 硬性规则

- 不跳过测试与验收报告。
- 不在当前模块里实现下游模块；下游未完成时使用接口桩。
- 不擅自修改其他模块的公开契约；契约变更必须先更新 `CLAUDE.md` 并记录影响。
- 不在 import 阶段初始化 DeepSeek 客户端。
- SQL 工具只读 `business.db`，必须白名单、LIMIT、超时。
- WS 鉴权只用一次性 token；路径操作必须做根目录包含校验。
- 文档与验收报告用中文；代码标识符用英文。
- `PRD.md` 为 GBK 编码，只读，不修改。
