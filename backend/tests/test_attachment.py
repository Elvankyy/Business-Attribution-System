import pytest

from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.config import get_settings
from app.workspace.service import (
    AttachmentNotFound,
    AttachmentService,
    ConversationService,
)
from app.workspace.storage import safe_path, save_upload


def create_conversation(client, auth_headers) -> str:
    response = client.post(
        "/api/chat/create",
        json={"title": "附件测试"},
        headers=auth_headers,
    )
    return response.json()["conversation_id"]


def upload_file(client, auth_headers, conversation_id: str, name: str = "报告.txt"):
    return client.post(
        "/api/attachment/upload",
        data={"conversation_id": conversation_id},
        files={"file": (name, b"hello", "text/plain")},
        headers=auth_headers,
    )


def test_upload_and_download(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    response = upload_file(client, auth_headers, conversation_id)

    assert response.status_code == 200
    body = response.json()
    assert body["file_name"] == "报告.txt"
    assert body["file_path"].startswith("uploads/")

    download = client.get(
        "/api/attachment/get",
        params={"attachment_id": body["attachment_id"]},
        headers=auth_headers,
    )
    assert download.status_code == 200
    assert download.content == b"hello"


def test_upload_sanitizes_traversal_filename(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    response = upload_file(client, auth_headers, conversation_id, name="../../evil.txt")

    assert response.status_code == 200
    body = response.json()
    assert body["file_name"] == "evil.txt"
    assert ".." not in body["file_path"]


def test_upload_to_missing_conversation_returns_404(client, auth_headers):
    response = client.post(
        "/api/attachment/upload",
        data={"conversation_id": "conv_missing"},
        files={"file": ("a.txt", b"x", "text/plain")},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_upload_requires_auth(client):
    response = client.post(
        "/api/attachment/upload",
        data={"conversation_id": "conv_any"},
        files={"file": ("a.txt", b"x", "text/plain")},
    )

    assert response.status_code == 401


def test_delete_attachment(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    uploaded = upload_file(client, auth_headers, conversation_id).json()

    deleted = client.post(
        "/api/attachment/delete",
        json={"attachment_id": uploaded["attachment_id"]},
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True

    download = client.get(
        "/api/attachment/get",
        params={"attachment_id": uploaded["attachment_id"]},
        headers=auth_headers,
    )
    assert download.status_code == 404


def test_delete_missing_attachment_returns_404(client, auth_headers):
    response = client.post(
        "/api/attachment/delete",
        json={"attachment_id": "att_missing"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_list_attachments(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    upload_file(client, auth_headers, conversation_id)
    client.post(
        "/api/attachment/upload",
        data={"conversation_id": conversation_id},
        files={"file": ("图片.png", b"image", "image/png")},
        headers=auth_headers,
    )

    response = client.get(
        "/api/attachment/ls",
        params={"conversation_id": conversation_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    names = {item["file_name"] for item in response.json()}
    assert {"报告.txt", "图片.png"} <= names


def test_list_attachments_missing_conversation(client, auth_headers):
    response = client.get(
        "/api/attachment/ls",
        params={"conversation_id": "conv_missing"},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_list_attachments_requires_auth(client):
    response = client.get(
        "/api/attachment/ls",
        params={"conversation_id": "conv_any"},
    )

    assert response.status_code == 401


def test_save_upload_rejects_oversize():
    with pytest.raises(ValueError):
        save_upload(b"1234", "u1", "c1", "att_x", "a.txt", max_bytes=3)


def test_safe_path_rejects_escape():
    with pytest.raises(ValueError):
        safe_path(get_settings().storage_path, "..", "evil.txt")


@pytest.mark.asyncio
async def test_attachment_ownership_service(db_session):
    auth_service = AuthService(db_session)
    owner = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m04-owner",
            username="m04-owner",
            display_name="Owner",
        )
    )
    other = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m04-other",
            username="m04-other",
            display_name="Other",
        )
    )
    conversation = await ConversationService(db_session).create(owner.id, "附件归属")
    service = AttachmentService(db_session)
    attachment = await service.upload(
        owner.id,
        conversation.id,
        "a.txt",
        b"x",
        "text/plain",
    )

    with pytest.raises(AttachmentNotFound):
        await service.get_download(other.id, attachment.id)
    with pytest.raises(AttachmentNotFound):
        await service.delete(other.id, attachment.id)
