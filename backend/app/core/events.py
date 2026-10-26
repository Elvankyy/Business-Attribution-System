from datetime import UTC, datetime
from typing import Any


def _event(event_type: str, **payload: Any) -> dict[str, Any]:
    return {"type": event_type, **payload}


def message_start(task_id: str, conversation_id: str) -> dict[str, Any]:
    return _event("message_start", task_id=task_id, conversation_id=conversation_id)


def message_delta(task_id: str, delta_text: str) -> dict[str, Any]:
    return _event("message_delta", task_id=task_id, delta_text=delta_text)


def tool_start(task_id: str, tool_name: str) -> dict[str, Any]:
    return _event("tool_start", task_id=task_id, tool_name=tool_name)


def tool_finish(
    task_id: str, tool_name: str, tool_result_summary: str
) -> dict[str, Any]:
    return _event(
        "tool_finish",
        task_id=task_id,
        tool_name=tool_name,
        tool_result_summary=tool_result_summary,
    )


def task_status(task_id: str, task_status_value: str, current_step: str) -> dict[str, Any]:
    return _event(
        "task_status",
        task_id=task_id,
        task_status=task_status_value,
        current_step=current_step,
    )


def result_ready(task_id: str, result_id: str) -> dict[str, Any]:
    return _event("result_ready", task_id=task_id, result_id=result_id)


def error(task_id: str, error_message: str) -> dict[str, Any]:
    return _event("error", task_id=task_id, error_message=error_message)


def done(task_id: str, finished_at: datetime | str | None) -> dict[str, Any]:
    if isinstance(finished_at, datetime):
        finished_at = finished_at.astimezone(UTC).isoformat()
    return _event("done", task_id=task_id, finished_at=finished_at)


def connected(conversation_id: str) -> dict[str, Any]:
    return _event("connected", conversation_id=conversation_id)


def pong() -> dict[str, Any]:
    return _event("pong")
