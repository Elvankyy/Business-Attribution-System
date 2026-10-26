import pytest
from starlette.websockets import WebSocketDisconnect

from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.events import task_status as build_task_status
from app.core.realtime import ConnectionManager
from app.workspace.service import (
    ConversationNotFound,
    ConversationService,
    WebSocketTokenService,
)


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, data: dict) -> None:
        self.messages.append(data)


def create_conversation(client, auth_headers) -> str:
    return client.post(
        "/api/chat/create",
        json={"title": "实时连接测试"},
        headers=auth_headers,
    ).json()["conversation_id"]


def issue_token(client, auth_headers, conversation_id: str) -> dict:
    return client.post(
        "/api/chat/ws-token",
        json={"conversation_id": conversation_id},
        headers=auth_headers,
    ).json()


def websocket_url(token: str, conversation_id: str) -> str:
    return (
        f"/api/chat/ws/chat?websocket_token={token}"
        f"&conversation_id={conversation_id}"
    )


@pytest.mark.asyncio
async def test_connection_manager_broadcast():
    manager = ConnectionManager()
    websocket = FakeWebSocket()

    await manager.connect("conv_1", websocket)
    assert manager.connection_count("conv_1") == 1

    await manager.broadcast(
        "conv_1",
        build_task_status("task_1", "running", "analyzing"),
    )
    assert websocket.messages[0]["type"] == "task_status"
    assert websocket.messages[0]["current_step"] == "analyzing"

    await manager.disconnect("conv_1", websocket)
    assert manager.connection_count("conv_1") == 0


def test_ws_token_and_handshake(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    token_response = issue_token(client, auth_headers, conversation_id)

    assert token_response["expires_in"] == 60
    token = token_response["websocket_token"]

    with client.websocket_connect(websocket_url(token, conversation_id)) as websocket:
        connected = websocket.receive_json()
        assert connected["type"] == "connected"
        assert connected["conversation_id"] == conversation_id

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json()["type"] == "pong"


def test_ws_token_single_use(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)
    token = issue_token(client, auth_headers, conversation_id)["websocket_token"]

    with client.websocket_connect(websocket_url(token, conversation_id)) as websocket:
        assert websocket.receive_json()["type"] == "connected"

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(
        websocket_url(token, conversation_id)
    ) as websocket:
        websocket.receive_json()


def test_ws_invalid_token(client, auth_headers):
    conversation_id = create_conversation(client, auth_headers)

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(
        websocket_url("invalid-token", conversation_id)
    ) as websocket:
        websocket.receive_json()


def test_ws_token_requires_auth(client):
    response = client.post(
        "/api/chat/ws-token",
        json={"conversation_id": "conv_any"},
    )

    assert response.status_code == 401


def test_ws_token_missing_conversation(client, auth_headers):
    response = client.post(
        "/api/chat/ws-token",
        json={"conversation_id": "conv_missing"},
        headers=auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_token_issue_ownership(db_session):
    auth_service = AuthService(db_session)
    owner = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m05-owner",
            username="m05-owner",
            display_name="Owner",
        )
    )
    other = await auth_service.upsert_user(
        AuthUserProfile(
            external_user_id="m05-other",
            username="m05-other",
            display_name="Other",
        )
    )
    conversation = await ConversationService(db_session).create(owner.id, "WS 归属")

    with pytest.raises(ConversationNotFound):
        await WebSocketTokenService(db_session).issue(other.id, conversation.id)
