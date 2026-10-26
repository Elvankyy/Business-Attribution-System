from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
YAML_PATH = PROJECT_ROOT / "docs" / "page-interface.yaml"
MARKDOWN_PATH = PROJECT_ROOT / "docs" / "page-interface.md"


def format_value(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, dict):
        if not value:
            return "—"
        return "、".join(f"{key}={item}" for key, item in value.items())
    if isinstance(value, list):
        return "、".join(str(item) for item in value) if value else "—"
    return str(value)


def status_label(status: str) -> str:
    return {
        "matched": "一致",
        "extension": "实现新增",
        "frontend_pending": "前端待接入",
        "missing": "后端缺失",
    }.get(status, status)


def render() -> Path:
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8"))
    lines: list[str] = [
        "# 页面接口文档",
        "",
        "> 本文件由 `docs/page-interface.yaml` 生成，请修改 YAML 后重新运行 `python -m scripts.render_page_interface`。",
        "",
        f"- 项目：{data.get('project', '')}",
        f"- 生成日期：{data.get('generated_on', '')}",
        "",
        "## 状态说明",
        "",
    ]
    for note in data.get("notes", []):
        lines.append(f"- {note}")
    lines.append("")

    actions = [
        action
        for page in data.get("pages", [])
        for action in page.get("actions", [])
    ]
    counts: dict[str, int] = {}
    for action in actions:
        status = action.get("status", "matched")
        counts[status] = counts.get(status, 0) + 1
    lines.append(
        "## 概览\n\n"
        f"- 页面数：{len(data.get('pages', []))}\n"
        f"- 动作数：{len(actions)}\n"
        + "\n".join(
            f"- {status_label(status)}：{count}"
            for status, count in sorted(counts.items())
        )
        + "\n"
    )

    for page in data.get("pages", []):
        lines.extend(
            [
                f"## {page.get('name', page.get('id', ''))}",
                "",
                f"- 路由：`{page.get('route', '')}`",
                f"- 组件：`{page.get('component', '')}`",
                "",
                "| 动作 | 类型 | 接口 | 请求 | 响应 | 错误 | 状态 |",
                "|---|---|---|---|---|---|---|",
            ]
        )
        for action in page.get("actions", []):
            interface = (
                f"`{action.get('method')} {action.get('path')}`"
                if action.get("method") and action.get("path")
                else "—"
            )
            lines.append(
                "| {name} | {kind} | {interface} | {request} | {response} | {errors} | {status} |".format(
                    name=action.get("name", ""),
                    kind=action.get("kind", ""),
                    interface=interface,
                    request=format_value(action.get("request")),
                    response=format_value(action.get("response")),
                    errors=format_value(action.get("errors")),
                    status=status_label(action.get("status", "matched")),
                )
            )
        lines.append("")

    websocket = data.get("websocket", {})
    if websocket:
        lines.extend(
            [
                "## WebSocket",
                "",
                f"- 端点：`{websocket.get('endpoint', '')}`",
                "",
                "### 服务端事件",
                "",
                "| 事件 | 字段 | 消费方 | 状态 |",
                "|---|---|---|---|",
            ]
        )
        for event in websocket.get("events", []):
            lines.append(
                f"| {event.get('type')} | {format_value(event.get('fields'))} | "
                f"{event.get('consumer', '')} | {status_label(event.get('status', 'matched'))} |"
            )
        lines.extend(
            [
                "",
                "### 客户端消息",
                "",
                "| 消息 | 字段 | 生产方 | 状态 |",
                "|---|---|---|---|",
            ]
        )
        for message in websocket.get("client_messages", []):
            lines.append(
                f"| {message.get('type')} | {format_value(message.get('fields'))} | "
                f"{message.get('producer', '')} | {status_label(message.get('status', 'matched'))} |"
            )
        lines.append("")

    backend_notes = data.get("backend_notes", [])
    if backend_notes:
        lines.extend(
            [
                "## 后端补充",
                "",
                "| 事项 | 说明 | 状态 |",
                "|---|---|---|",
            ]
        )
        for note in backend_notes:
            lines.append(
                f"| {note.get('id')} | {note.get('description')} | "
                f"{status_label(note.get('status', 'matched'))} |"
            )
        lines.append("")

    todos = data.get("frontend_todos", [])
    if todos:
        lines.append("## 前端待办\n")
        for todo in todos:
            lines.append(f"- [ ] {todo}")
        lines.append("")

    MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")
    return MARKDOWN_PATH


def main() -> None:
    path = render()
    print(f"written={path}")


if __name__ == "__main__":
    main()
