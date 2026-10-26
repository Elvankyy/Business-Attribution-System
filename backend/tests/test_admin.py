import pytest

from app.admin.service import ConfigService
from app.analysis.service import AnalysisTaskService
from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService, create_access_token
from app.core.models import SystemConfig, TaskLog


async def create_admin_headers(db_session) -> dict[str, str]:
    admin = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m09-admin",
            username="m09-admin",
            display_name="Admin",
            role="admin",
        )
    )
    token = create_access_token(admin)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_reload_and_list(client, db_session):
    db_session.add(
        SystemConfig(
            config_key="feature.demo",
            config_value="on",
            config_group="feature",
        )
    )
    await db_session.commit()
    headers = await create_admin_headers(db_session)

    reload_response = client.post("/api/admin/reload", headers=headers)
    assert reload_response.status_code == 200
    assert reload_response.json()["status"] == "ok"

    configs = client.get("/api/admin/configs", headers=headers)
    assert configs.status_code == 200
    assert any(
        item["config_key"] == "feature.demo" for item in configs.json()
    )
    assert ConfigService().get("feature.demo") == "on"


def test_reload_requires_admin(client, auth_headers):
    response = client.post("/api/admin/reload", headers=auth_headers)

    assert response.status_code == 403


def test_admin_requires_auth(client):
    assert client.post("/api/admin/reload").status_code == 401


@pytest.mark.asyncio
async def test_config_service_reload(db_session):
    db_session.add(
        SystemConfig(
            config_key="test.key",
            config_value="v",
            config_group="test",
        )
    )
    await db_session.commit()

    configs = await ConfigService().reload(db_session)

    assert configs["test.key"] == "v"


@pytest.mark.asyncio
async def test_admin_logs(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    conversation_id = client.post(
        "/api/chat/create",
        json={"title": "日志测试"},
        headers=auth_headers,
    ).json()["conversation_id"]
    task = await AnalysisTaskService(db_session).create(
        current_user["id"], conversation_id, "日志任务"
    )
    db_session.add(
        TaskLog(
            task_id=task.id,
            log_level="info",
            log_type="system",
            log_content="admin log test",
        )
    )
    await db_session.commit()

    headers = await create_admin_headers(db_session)
    response = client.get("/api/admin/logs", headers=headers)
    assert response.status_code == 200
    assert any(
        item["log_content"] == "admin log test" for item in response.json()
    )

    forbidden = client.get("/api/admin/logs", headers=auth_headers)
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_admin_tasks(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    conversation_id = client.post(
        "/api/chat/create",
        json={"title": "管理任务记录"},
        headers=auth_headers,
    ).json()["conversation_id"]
    task = await AnalysisTaskService(db_session).create(
        current_user["id"], conversation_id, "管理端任务"
    )

    headers = await create_admin_headers(db_session)
    response = client.get("/api/admin/tasks", headers=headers)

    assert response.status_code == 200
    items = response.json()
    assert any(
        item["task_id"] == task.id
        and item["conversation_title"] == "管理任务记录"
        and item["username"] == current_user["username"]
        for item in items
    )

    forbidden = client.get("/api/admin/tasks", headers=auth_headers)
    assert forbidden.status_code == 403
