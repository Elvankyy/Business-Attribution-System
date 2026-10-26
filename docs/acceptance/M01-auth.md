# M01 认证接入 验收报告

- 验收日期：2026-10-23
- 环境：Python 3.12.7、FastAPI 0.161.1、PyJWT 2.15.1、SQLAlchemy 2.1.6、SQLite
- 关联需求：PRD 2.1.2 用户角色、2.1.6 认证接入模块、2.1.9 登录与回调接口、2.1.13 授权登录验收标准
- 交付物：
  - `backend/app/auth/adapter.py`
  - `backend/app/auth/schemas.py`
  - `backend/app/auth/service.py`
  - `backend/app/auth/router.py`
  - `backend/app/core/dependencies.py`（`get_current_user`）
  - `backend/app/main.py`（注册认证路由）
  - `backend/tests/test_auth.py`

## 测试项与结果

| 编号 | 测试项 | 步骤 | 预期结果 | 实际结果 | 结论 |
|---|---|---|---|---|---|
| 1 | 登录跳转 | `GET /auth/login`，不跟随重定向 | 302，跳转 `/auth/callback` 并携带 `code=demo` 与签名 state | 符合预期 | 通过 |
| 2 | 回调登录 | 用有效 state 调 `GET /auth/callback` | 302，跳转前端并携带 JWT，用户写入 `users` | 符合预期 | 通过 |
| 3 | 当前用户 | 携带 Bearer Token 调 `GET /api/me` | 200，返回 demo 用户信息 | 符合预期 | 通过 |
| 4 | 非法 state | 用无效 state 调回调 | 400 | 返回 400 | 通过 |
| 5 | 非法 code | 用有效 state、错误 code 调回调 | 400 | 返回 400 | 通过 |
| 6 | 缺少 token | 不带 Authorization 调 `/api/me` | 401 | 返回 401 | 通过 |
| 7 | 非法 token | 携带无效 Bearer Token 调 `/api/me` | 401 | 返回 401 | 通过 |
| 8 | 重复登录 | 连续两次登录 | 复用同一个用户 ID | 用户 ID 一致 | 通过 |
| 9 | 用户更新 | 用同一 `external_user_id` 更新资料 | 同一用户 ID，字段更新 | 符合预期 | 通过 |
| 10 | 全量测试 | `uv run pytest -q` | 全部通过 | 13 passed | 通过 |
| 11 | 代码规范 | `uv run ruff check app tests scripts` | 无错误 | All checks passed | 通过 |
| 12 | 真实 HTTP 冒烟 | 启动 uvicorn，依次请求 `/auth/login`、`/auth/callback`、`/api/me` | 302、302、200 | 302、302、200，用户为 demo/analyst | 通过 |

## 验收标准核对

- [x] 能完成 Demo 授权登录并拿到 JWT。
- [x] 受保护接口在无 token 时返回 401。
- [x] 非法 state 被拒绝。
- [x] 用户信息正确写入 `users`。
- [x] 单元测试与接口测试通过。

## 问题与修复

1. **JWT 密钥长度告警**：默认密钥 21 字节，PyJWT 提示低于 SHA256 推荐的 32 字节。已把默认值与项目根 `.env.example` 改为 32 字节以上，告警消失。

## 遗留项

- 当前 state 使用签名 JWT 校验，但没有服务端一次性消费记录；10 分钟内可重放。Demo 阶段可接受，接入真实认证中心时应改用服务端 state/nonce 存储。
- 真实认证中心适配器 `HttpAuthCenter` 目前是接口桩，待真实认证中心参数确定后实现。
- `/api/me` 是为前端登录态校验补充的辅助接口，已同步写入 `CLAUDE.md` 与 `项目规划.md`。

## 结论

通过。
