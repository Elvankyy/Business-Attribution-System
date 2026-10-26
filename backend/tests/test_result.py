import asyncio

import pytest
from sqlalchemy import select

from app.analysis.agent.output import AnalysisOutput, Evidence, KeyMetric
from app.analysis.coordinator import AnalysisCoordinator
from app.analysis.service import (
    AnalysisResultService,
    AnalysisTaskService,
    ContextSummaryService,
    ResultNotFound,
)
from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.models import AnalysisResult, AnalysisTask, Message
from app.workspace.service import ConversationService, MessageService


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, conversation_id: str, event: dict) -> None:
        self.events.append((conversation_id, event))


class FakeRunner:
    def __init__(self, output: AnalysisOutput) -> None:
        self.output = output

    async def run(self, *, task_id, user_id, conversation_id, input_text):
        return self.output


def valid_output() -> AnalysisOutput:
    return AnalysisOutput(
        problem_definition="为什么订单量下降",
        key_metrics=[
            KeyMetric(
                metric_name="订单量",
                metric_value=100,
                metric_unit="单",
                metric_period="本月",
            )
        ],
        evidence_list=[
            Evidence(
                source_type="database",
                source_name="business.db",
                evidence_text="订单量下降 20%",
                related_metric="订单量",
                confidence=0.8,
            )
        ],
        conclusion_text="主要原因是华东区域订单下降",
        missing_data_text="缺少竞品价格数据",
        next_action_text="- 检查华东渠道投放\n- 补充竞品价格数据",
    )


async def create_owner_conversation_task(db_session, suffix: str):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id=f"m08-owner-{suffix}",
            username=f"m08-owner-{suffix}",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, f"结果测试-{suffix}"
    )
    task = await AnalysisTaskService(db_session).create(
        owner.id, conversation.id, "分析问题"
    )
    return owner, conversation, task


async def wait_for_status(task_id: str, expected: str, timeout: float = 2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        async with SessionLocal() as session:
            task = await session.get(AnalysisTask, task_id)
            if task is not None and task.task_status == expected:
                return task
        await asyncio.sleep(0.02)
    raise AssertionError(f"task status is not {expected}")


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
async def test_save_output_persists_and_exports(db_session):
    owner, _, task = await create_owner_conversation_task(db_session, "save")
    service = AnalysisResultService(db_session)

    result = await service.save_output(task, valid_output())

    assert result.task_id == task.id
    assert result.key_metrics_json[0]["metric_name"] == "订单量"
    assert result.evidence_list_json[0]["source_name"] == "business.db"
    assert "经营归因分析报告" in result.result_markdown
    assert (get_settings().storage_path / result.result_file_path).exists()

    fetched = await service.get_for_user(task.id, owner.id)
    assert fetched is not None
    assert fetched.id == result.id


@pytest.mark.asyncio
async def test_result_ownership(db_session):
    _, _, task = await create_owner_conversation_task(db_session, "owner")
    other = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m08-other",
            username="m08-other",
            display_name="Other",
        )
    )
    service = AnalysisResultService(db_session)
    await service.save_output(task, valid_output())

    assert await service.get_for_user(task.id, other.id) is None
    with pytest.raises(ResultNotFound):
        await service.get_file_for_user(task.id, other.id)


@pytest.mark.asyncio
async def test_result_api_and_file_download(client, auth_headers, db_session):
    current_user = client.get("/api/me", headers=auth_headers).json()
    conversation_id = client.post(
        "/api/chat/create",
        json={"title": "结果接口"},
        headers=auth_headers,
    ).json()["conversation_id"]
    task = await AnalysisTaskService(db_session).create(
        current_user["id"], conversation_id, "接口结果"
    )
    await AnalysisResultService(db_session).save_output(task, valid_output())

    response = client.get(f"/api/results/{task.id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["problem_definition"] == "为什么订单量下降"
    assert body["key_metrics"][0]["metric_name"] == "订单量"
    assert "next_action_text" in body

    file_response = client.get(
        f"/api/results/{task.id}/file", headers=auth_headers
    )
    assert file_response.status_code == 200
    assert "经营归因分析报告" in file_response.content.decode("utf-8")

    missing = client.get("/api/results/task_missing", headers=auth_headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_context_summary_compression(db_session):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m08-summary-owner",
            username="m08-summary-owner",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, "摘要测试"
    )
    message_service = MessageService(db_session)
    for index in range(15):
        await message_service.append(
            owner.id,
            conversation.id,
            "user" if index % 2 == 0 else "assistant",
            f"消息 {index + 1}",
        )

    summary = await ContextSummaryService(db_session).compress(
        conversation.id, keep_recent=10
    )

    assert summary is not None
    assert summary.start_seq_no == 1
    assert summary.end_seq_no == 5

    again = await ContextSummaryService(db_session).compress(
        conversation.id, keep_recent=10
    )
    assert again is None


@pytest.mark.asyncio
async def test_coordinator_saves_result_and_emits_ready(db_session):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m08-coordinator-owner",
            username="m08-coordinator-owner",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, "结果测试-coordinator"
    )
    publisher = FakePublisher()
    coordinator = AnalysisCoordinator(
        runner=FakeRunner(valid_output()), publisher=publisher
    )

    task = await coordinator.start_analysis(
        owner.id, conversation.id, "分析问题"
    )
    await wait_for_status(task.id, "success")
    await wait_for_event(publisher, "result_ready")
    await wait_for_event(publisher, "done")

    async with SessionLocal() as session:
        stored = (
            await session.execute(
                select(AnalysisResult).where(
                    AnalysisResult.task_id == task.id
                )
            )
        ).scalar_one_or_none()
        assistant_messages = (
            await session.execute(
                select(Message).where(
                    Message.conversation_id == conversation.id,
                    Message.role == "assistant",
                )
            )
        ).scalars().all()

    assert stored is not None
    assert stored.problem_definition == "为什么订单量下降"
    assert any(
        message.message_type == "analysis"
        and message.content == "主要原因是华东区域订单下降"
        for message in assistant_messages
    )
