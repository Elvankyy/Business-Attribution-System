from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.config import get_settings
from app.core.models import (
    AnalysisResult,
    AnalysisTask,
    Attachment,
    ContextSummary,
    Conversation,
    Message,
    TaskLog,
    WebsocketToken,
    get_uid,
)
from app.workspace.service import ConversationNotFound, ConversationService


def test_create_and_list_conversation(client, auth_headers):
    created = client.post(
        "/api/chat/create",
        json={"title": "分析会话"},
        headers=auth_headers,
    )
    assert created.status_code == 200
    body = created.json()
    assert body["title"] == "分析会话"
    assert body["status"] == "active"
    conversation_id = body["conversation_id"]

    listed = client.get("/api/chat/ls", headers=auth_headers)
    assert listed.status_code == 200
    items = listed.json()
    assert any(item["conversation_id"] == conversation_id for item in items)
    assert all("last_message_at" in item for item in items)


def test_create_uses_default_title(client, auth_headers):
    response = client.post("/api/chat/create", json={}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["title"] == "新会话"


def test_update_conversation(client, auth_headers):
    created = client.post(
        "/api/chat/create",
        json={"title": "旧标题"},
        headers=auth_headers,
    ).json()

    response = client.post(
        "/api/chat/update",
        json={"conversation_id": created["conversation_id"], "title": "新标题"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "新标题"

    listed = client.get("/api/chat/ls", headers=auth_headers).json()
    item = next(
        item for item in listed if item["conversation_id"] == created["conversation_id"]
    )
    assert item["title"] == "新标题"


def test_update_missing_conversation_returns_404(client, auth_headers):
    response = client.post(
        "/api/chat/update",
        json={"conversation_id": "conv_missing", "title": "x"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_conversation(client, auth_headers):
    created = client.post(
        "/api/chat/create",
        json={"title": "待删除"},
        headers=auth_headers,
    ).json()

    response = client.post(
        "/api/chat/delete",
        json={"conversation_ids": [created["conversation_id"]]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == 1

    listed = client.get("/api/chat/ls", headers=auth_headers).json()
    assert all(item["conversation_id"] != created["conversation_id"] for item in listed)


def test_delete_unknown_conversation_returns_zero(client, auth_headers):
    response = client.post(
        "/api/chat/delete",
        json={"conversation_ids": ["conv_missing"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["deleted"] == 0


def test_requires_auth(client):
    assert client.get("/api/chat/ls").status_code == 401


@pytest.mark.asyncio
async def test_ownership_and_cascade_delete(db_session):
    auth_service = AuthService(db_session)
    owner = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m02-owner",
            username="m02-owner",
            display_name="Owner",
        )
    )
    other = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m02-other",
            username="m02-other",
            display_name="Other",
        )
    )

    service = ConversationService(db_session)
    conversation = await service.create(owner.id, "级联删除测试")

    assert await service.list_for_user(other.id) == []
    with pytest.raises(ConversationNotFound):
        await service.update_title(other.id, conversation.id, "越权修改")

    message = Message(
        conversation_id=conversation.id,
        role="user",
        message_type="text",
        content="hi",
        seq_no=1,
    )
    db_session.add(message)
    await db_session.flush()

    attachment = Attachment(
        conversation_id=conversation.id,
        message_id=message.id,
        file_name="a.txt",
        file_path="uploads/a.txt",
    )
    task = AnalysisTask(
        conversation_id=conversation.id,
        user_id=owner.id,
        input_text="分析",
        task_status="queued",
    )
    db_session.add_all([attachment, task])
    await db_session.flush()

    result = AnalysisResult(task_id=task.id, conversation_id=conversation.id)
    summary = ContextSummary(
        conversation_id=conversation.id,
        start_seq_no=1,
        end_seq_no=1,
        summary_text="summary",
    )
    token = WebsocketToken(
        user_id=owner.id,
        conversation_id=conversation.id,
        token=get_uid("tok"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    log = TaskLog(
        task_id=task.id,
        log_level="info",
        log_type="system",
        log_content="log",
    )
    db_session.add_all([result, summary, token, log])
    await db_session.commit()

    for group in ("uploads", "exports", "workspace"):
        (get_settings().storage_path / group / owner.id / conversation.id).mkdir(
            parents=True,
            exist_ok=True,
        )

    deleted = await service.delete(owner.id, [conversation.id])
    assert deleted == 1

    async def count(model, condition) -> int:
        result = await db_session.execute(
            select(func.count()).select_from(model).where(condition)
        )
        return result.scalar_one()

    assert await count(Conversation, Conversation.id == conversation.id) == 0
    assert await count(Message, Message.conversation_id == conversation.id) == 0
    assert await count(Attachment, Attachment.conversation_id == conversation.id) == 0
    assert await count(AnalysisTask, AnalysisTask.conversation_id == conversation.id) == 0
    assert (
        await count(AnalysisResult, AnalysisResult.conversation_id == conversation.id) == 0
    )
    assert await count(ContextSummary, ContextSummary.conversation_id == conversation.id) == 0
    assert (
        await count(WebsocketToken, WebsocketToken.conversation_id == conversation.id) == 0
    )
    assert await count(TaskLog, TaskLog.task_id == task.id) == 0

    for group in ("uploads", "exports", "workspace"):
        assert not (get_settings().storage_path / group / owner.id / conversation.id).exists()
