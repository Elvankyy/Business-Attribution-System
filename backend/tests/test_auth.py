from urllib.parse import parse_qs, urlparse

import pytest

from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService


def extract_query(url: str) -> dict[str, str]:
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


def login_and_get_token(client) -> str:
    login = client.get("/auth/login", follow_redirects=False)
    assert login.status_code == 302
    state = extract_query(login.headers["location"])["state"]

    callback = client.get(
        "/auth/callback",
        params={"code": "demo", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    return callback.headers["location"].split("#token=", 1)[1]


def test_demo_login_flow(client):
    token = login_and_get_token(client)

    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["username"] == "demo"
    assert body["display_name"] == "演示用户"
    assert body["role"] == "analyst"
    assert body["status"] == "active"


def test_callback_rejects_invalid_state(client):
    response = client.get(
        "/auth/callback",
        params={"code": "demo", "state": "invalid-state"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_callback_rejects_invalid_code(client):
    login = client.get("/auth/login", follow_redirects=False)
    state = extract_query(login.headers["location"])["state"]

    response = client.get(
        "/auth/callback",
        params={"code": "wrong", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_me_requires_token(client):
    response = client.get("/api/me")
    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get("/api/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401


def test_login_reuses_same_user(client):
    first = login_and_get_token(client)
    second = login_and_get_token(client)

    first_user = client.get(
        "/api/me", headers={"Authorization": f"Bearer {first}"}
    ).json()
    second_user = client.get(
        "/api/me", headers={"Authorization": f"Bearer {second}"}
    ).json()

    assert first_user["id"] == second_user["id"]


def test_demo_admin_login(client):
    login = client.get(
        "/auth/login",
        params={"as_admin": True},
        follow_redirects=False,
    )
    state = extract_query(login.headers["location"])["state"]
    callback = client.get(
        "/auth/callback",
        params={"code": "demo", "state": state},
        follow_redirects=False,
    )
    token = callback.headers["location"].split("#token=", 1)[1]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    configs = client.get("/api/admin/configs", headers=headers)
    assert configs.status_code == 200


@pytest.mark.asyncio
async def test_upsert_user_updates_profile(db_session):
    service = AuthService(db_session)
    profile = AuthUserProfile(
        external_user_id="test-upsert-user",
        username="test-upsert",
        display_name="新名称",
        role="admin",
    )

    user = await service.upsert_user(profile)

    assert user.display_name == "新名称"
    assert user.role == "admin"

    updated = await service.upsert_user(
        AuthUserProfile(
            external_user_id="test-upsert-user",
            username="test-upsert",
            display_name="更新后的名称",
            role="analyst",
        )
    )

    assert updated.id == user.id
    assert updated.display_name == "更新后的名称"
    assert updated.role == "analyst"
