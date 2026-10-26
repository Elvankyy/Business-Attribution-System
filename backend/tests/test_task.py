import asyncio

import pytest

from app.analysis.coordinator import AnalysisCoordinator
from app.analysis.service import (
    AnalysisTaskService,
    TaskAlreadyRunning,
    TaskNotFound,
)
from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.database import SessionLocal
from app.core.models import AnalysisResult, AnalysisTask, TaskLog
from app.workspace.service import ConversationNotFound, ConversationService


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, conversation_id: str, event: dict) -> None:
        self.events.append((conversation_id, event))


class FakeRunner:
    def __init__(self, block: asyncio.Event | None = None, fail: bool = False) -> None:
        self.block = block
        self.fail = fail

    async def run(self, *, task_id, user_id, conversation_id, input_text):
        if self.block is not None:
            await self.block.wait()
        if self.fail:
            raise RuntimeError("boom")


async def create_owner_conversation(db_session, suffix: str):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id=f"m06-owner-{suffix}",
            username=f"m06-owner-{suffix}",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, f"任务测试-{suffix}"
    )
    return owner, conversation


async def get_task(task_id: str) -> AnalysisTask | None:
    async with SessionLocal() as session:
        return await session.get(AnalysisTask, task_id)


async def wait_for_status(task_id: str, expected: str, timeout: float = 2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        task = await get_task(task_id)
        if task is not None and task.task_status == expected:
            return task
        await asyncio.sleep(0.02)

    task = await get_task(task_id)
    actual = task.task_status if task is not None else None
    raise AssertionError(f"task status is {actual}, expected {expected}")


async def wait_for_event(
    publisher: FakePublisher, event_type: str, timeout: float = 2.0
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if any(event["type"] == event_type for _, event in publisher.events):
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"event {event_type} was not published")


@pytest.mark.asyncio
async def test_success_flow(db_session):
    owner, conversation = await create_owner_conversation(db_session, "success")
    publisher = FakePublisher()
    coordinator = AnalysisCoordinator(runner=FakeRunner(), publisher=publisher)

    task = await coordinator.start_analysis(owner.id, conversation.id, "分析问题")
    await wait_for_status(task.id, "success")
    await wait_for_event(publisher, "done")

    event_types = [event["type"] for _, event in publisher.events]
    assert "message_start" in event_types
    assert "task_status" in event_types
    assert event_types[-1] == "done"


@pytest.mark.asyncio
async def test_one_active_task_per_conversation(db_session):
    owner, conversation = await create_owner_conversation(db_session, "single")
    block = asyncio.Event()
    coordinator = AnalysisCoordinator(
        runner=FakeRunner(block=block), publisher=FakePublisher()
    )

    first = await coordinator.start_analysis(owner.id, conversation.id, "第一个")
    await wait_for_status(first.id, "running")

    with pytest.raises(TaskAlreadyRunning):
        await coordinator.start_analysis(owner.id, conversation.id, "第二个")

    block.set()
    await wait_for_status(first.id, "success")


@pytest.mark.asyncio
async def test_cancel_running_task(db_session):
    owner, conversation = await create_owner_conversation(db_session, "cancel")
    block = asyncio.Event()
    publisher = FakePublisher()
    coordinator = AnalysisCoordinator(
        runner=FakeRunner(block=block), publisher=publisher
    )

    task = await coordinator.start_analysis(owner.id, conversation.id, "取消测试")
    await wait_for_status(task.id, "running")

    cancelled = await coordinator.cancel(task.id, owner.id)
    assert cancelled.task_status == "cancelled"
    await wait_for_status(task.id, "cancelled")
    block.set()

    event_types = [event["type"] for _, event in publisher.events]
    assert "done" in event_types


@pytest.mark.asyncio
async def test_failure_flow(db_session):
    owner, conversation = await create_owner_conversation(db_session, "failure")
    publisher = FakePublisher()
    coordinator = AnalysisCoordinator(
        runner=FakeRunner(fail=True), publisher=publisher
    )

    task = await coordinator.start_analysis(owner.id, conversation.id, "失败测试")
    failed = await wait_for_status(task.id, "failed")
    await wait_for_event(publisher, "done")

    assert failed.error_message == "boom"
    assert any(event["type"] == "error" for _, event in publisher.events)


@pytest.mark.asyncio
async def test_recover_stale_tasks(db_session):
    owner, conversation = await create_owner_conversation(db_session, "recover")
    service = AnalysisTaskService(db_session)
    task = await service.create(owner.id, conversation.id, "中断任务")
    await service.update_status(task, "running")

    coordinator = AnalysisCoordinator(publisher=FakePublisher())
    count = await coordinator.recover_stale_tasks()

    assert count >= 1
    recovered = await get_task(task.id)
    assert recovered is not None
    assert recovered.task_status == "failed"


@pytest.mark.asyncio
async def test_task_api_get_and_cancel(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    conversation_id = client.post(
        "/api/chat/create",
        json={"title": "API 任务"},
        headers=auth_headers,
    ).json()["conversation_id"]

    task = await AnalysisTaskService(db_session).create(
        current_user["id"], conversation_id, "接口任务"
    )

    response = client.get(f"/api/tasks/{task.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["task_status"] == "queued"

    cancelled = client.post(f"/api/tasks/{task.id}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["task_status"] == "cancelled"


@pytest.mark.asyncio
async def test_task_ownership(db_session):
    owner, conversation = await create_owner_conversation(db_session, "owner")
    other = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m06-other",
            username="m06-other",
            display_name="Other",
        )
    )
    service = AnalysisTaskService(db_session)
    task = await service.create(owner.id, conversation.id, "归属测试")

    assert await service.get_for_user(task.id, other.id) is None
    with pytest.raises(TaskNotFound):
        await service.cancel(task.id, other.id)


@pytest.mark.asyncio
async def test_task_list_and_logs_api(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    conversation_id = client.post(
        "/api/chat/create",
        json={"title": "任务列表"},
        headers=auth_headers,
    ).json()["conversation_id"]

    service = AnalysisTaskService(db_session)
    task = await service.create(
        current_user["id"], conversation_id, "列表测试"
    )
    result = AnalysisResult(
        task_id=task.id,
        conversation_id=conversation_id,
        problem_definition="问题定义",
    )
    log = TaskLog(
        task_id=task.id,
        log_level="info",
        log_type="tool",
        log_content="sql_query 执行完成",
    )
    db_session.add_all([result, log])
    await db_session.commit()

    tasks_response = client.get(
        "/api/tasks",
        params={"conversation_id": conversation_id},
        headers=auth_headers,
    )
    assert tasks_response.status_code == 200
    items = tasks_response.json()
    assert any(
        item["task_id"] == task.id and item["result_id"] == result.id
        for item in items
    )

    logs_response = client.get(
        f"/api/tasks/{task.id}/logs", headers=auth_headers
    )
    assert logs_response.status_code == 200
    assert any(
        item["log_content"] == "sql_query 执行完成"
        for item in logs_response.json()
    )


@pytest.mark.asyncio
async def test_task_list_and_logs_ownership(db_session):
    owner, conversation = await create_owner_conversation(db_session, "list-owner")
    other = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m06-list-other",
            username="m06-list-other",
            display_name="Other",
        )
    )
    service = AnalysisTaskService(db_session)
    task = await service.create(owner.id, conversation.id, "归属列表")

    with pytest.raises(ConversationNotFound):
        await service.list_for_conversation(other.id, conversation.id)
    with pytest.raises(TaskNotFound):
        await service.list_logs(task.id, other.id)
