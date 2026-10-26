import pytest

from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.models import Attachment
from app.workspace.service import (
    ConversationNotFound,
    ConversationService,
    MessageService,
)


async def create_owner_and_conversation(db_session, suffix: str):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id=f"m03-owner-{suffix}",
            username=f"m03-owner-{suffix}",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, f"消息测试-{suffix}"
    )
    return owner, conversation


@pytest.mark.asyncio
async def test_append_messages_seq_order_and_last_message_at(db_session):
    owner, conversation = await create_owner_and_conversation(db_session, "order")
    service = MessageService(db_session)

    first = await service.append(owner.id, conversation.id, "user", "问题一")
    second = await service.append(
        owner.id,
        conversation.id,
        "tool",
        "查询结果",
        message_type="tool_call",
        tool_name="sql_query",
        tool_status="success",
    )
    third = await service.append(owner.id, conversation.id, "assistant", "结论")

    assert [first.seq_no, second.seq_no, third.seq_no] == [1, 2, 3]
    assert second.tool_name == "sql_query"
    assert second.tool_status == "success"

    await db_session.refresh(conversation)
    assert conversation.last_message_at is not None

    history = await service.list_history_with_attachments(owner.id, conversation.id)
    assert [message.seq_no for message, _ in history] == [1, 2, 3]
    assert history[0][0].content == "问题一"


@pytest.mark.asyncio
async def test_history_includes_attachments(db_session):
    owner, conversation = await create_owner_and_conversation(db_session, "attachment")
    service = MessageService(db_session)
    message = await service.append(owner.id, conversation.id, "user", "带附件")

    attachment = Attachment(
        conversation_id=conversation.id,
        message_id=message.id,
        file_name="报告.pdf",
        file_path="uploads/report.pdf",
        file_type="application/pdf",
        file_size=10,
    )
    db_session.add(attachment)
    await db_session.commit()

    history = await service.list_history_with_attachments(owner.id, conversation.id)
    assert history[0][1][0].file_name == "报告.pdf"


@pytest.mark.asyncio
async def test_history_ownership(db_session):
    _owner, conversation = await create_owner_and_conversation(db_session, "owner")
    other = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m03-other",
            username="m03-other",
            display_name="Other",
        )
    )

    with pytest.raises(ConversationNotFound):
        await MessageService(db_session).list_history_with_attachments(
            other.id, conversation.id
        )


@pytest.mark.asyncio
async def test_invalid_role_rejected(db_session):
    owner, conversation = await create_owner_and_conversation(db_session, "role")

    with pytest.raises(ValueError):
        await MessageService(db_session).append(
            owner.id, conversation.id, "invalid", "内容"
        )


def test_history_empty_conversation(client, auth_headers):
    created = client.post(
        "/api/chat/create",
        json={"title": "空会话"},
        headers=auth_headers,
    ).json()

    response = client.get(
        f"/api/chat/ls/{created['conversation_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_history_missing_conversation_returns_404(client, auth_headers):
    response = client.get("/api/chat/ls/conv_missing", headers=auth_headers)

    assert response.status_code == 404


def test_history_requires_auth(client):
    assert client.get("/api/chat/ls/anything").status_code == 401


@pytest.mark.asyncio
async def test_history_api_returns_messages(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    created = client.post(
        "/api/chat/create",
        json={"title": "API 历史"},
        headers=auth_headers,
    ).json()

    await MessageService(db_session).append(
        current_user["id"],
        created["conversation_id"],
        "user",
        "你好",
    )

    response = client.get(
        f"/api/chat/ls/{created['conversation_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["content"] == "你好"
    assert body[0]["message_type"] == "text"
    assert body[0]["attachments"] == []
