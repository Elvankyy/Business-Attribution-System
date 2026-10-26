import json
import sqlite3
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.analysis.agent.factory import create_model
from app.analysis.agent.output import AnalysisOutput, Evidence, KeyMetric
from app.analysis.harness.context import ContextCompiler
from app.analysis.harness.executor import AgentExecutor
from app.analysis.harness.runtime import (
    AgentRuntimeContext,
    AnalysisExecutionState,
    ToolCallRecord,
)
from app.analysis.harness.tools import SqlQueryTool, TextSearchTool, ToolExecutor
from app.analysis.harness.validator import AnalysisOutputValidator
from app.analysis.service import AnalysisTaskService
from app.auth.adapter import AuthUserProfile
from app.auth.service import AuthService
from app.core.database import SessionLocal
from app.core.models import ContextSummary, Message, TaskLog
from app.workspace.service import ConversationService, MessageService


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def publish(self, conversation_id: str, event: dict) -> None:
        self.events.append((conversation_id, event))


class FakeAgent:
    def __init__(self, outputs: list[AnalysisOutput]) -> None:
        self.outputs = outputs
        self.calls = 0

    async def astream_events(self, input, version="v2", config=None):
        index = min(self.calls, len(self.outputs) - 1)
        self.calls += 1
        yield {
            "event": "on_chat_model_stream",
            "data": {"chunk": SimpleNamespace(content="分析片段")},
        }
        yield {
            "event": "on_chain_end",
            "data": {"output": {"structured_response": self.outputs[index]}},
        }


@pytest.fixture
def business_db(tmp_path):
    path = tmp_path / "business.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount REAL, region TEXT)"
    )
    connection.executemany(
        "INSERT INTO orders (id, amount, region) VALUES (?, ?, ?)",
        [(1, 100, "华东"), (2, 200, "华南"), (3, 300, "华东")],
    )
    connection.execute(
        "CREATE VIRTUAL TABLE documents_fts USING fts5(source_name, content)"
    )
    connection.execute(
        "INSERT INTO documents_fts (source_name, content) VALUES (?, ?)",
        ("doc1", "退款原因是质量问题"),
    )
    connection.commit()
    connection.close()
    return str(path)


def valid_output(source_name: str = "business.db") -> AnalysisOutput:
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
                source_name=source_name,
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
            external_user_id=f"m07-owner-{suffix}",
            username=f"m07-owner-{suffix}",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(
        owner.id, f"分析测试-{suffix}"
    )
    task = await AnalysisTaskService(db_session).create(
        owner.id, conversation.id, "分析问题"
    )
    return owner, conversation, task


@pytest.mark.asyncio
async def test_sql_tool_rows_and_limit(business_db):
    tool = SqlQueryTool(business_db, {"orders"}, max_rows=2, timeout_seconds=2)

    result = await tool.run("SELECT * FROM orders ORDER BY id")

    assert result.success is True
    assert len(result.data["rows"]) == 2
    assert result.data["rows"][0]["id"] == 1


@pytest.mark.asyncio
async def test_sql_tool_rejects_unsafe_queries(business_db):
    tool = SqlQueryTool(business_db, {"orders"}, max_rows=10, timeout_seconds=2)

    assert (await tool.run("SELECT * FROM secrets")).success is False
    assert (await tool.run("DELETE FROM orders")).success is False
    assert (await tool.run("SELECT * FROM orders; DROP TABLE orders")).success is False
    assert (await tool.run("SELECT * FROM orders -- comment")).success is False
    assert (await tool.run("")).success is False


@pytest.mark.asyncio
async def test_text_search(business_db):
    tool = TextSearchTool(business_db)

    result = await tool.run("退款")

    assert result.success is True
    assert result.data["results"][0]["source_name"] == "doc1"


def test_validator_accepts_and_rejects():
    validator = AnalysisOutputValidator()
    tool_results = [
        ToolCallRecord(
            tool_name="sql_query",
            source_name="business.db",
            summary="查询返回 1 行",
            success=True,
        )
    ]

    assert validator.validate(valid_output(), tool_results) == []

    invalid_source = validator.validate(valid_output("fake"), tool_results)
    assert any("来源无法追溯" in error for error in invalid_source)

    one_action = valid_output().model_copy(update={"next_action_text": "- 仅一条"})
    assert any("至少需要 2 条" in error for error in validator.validate(one_action, tool_results))


@pytest.mark.asyncio
async def test_executor_streams_and_returns_output():
    publisher = FakePublisher()
    state = AnalysisExecutionState(
        tool_results=[
            ToolCallRecord(
                tool_name="sql_query",
                source_name="business.db",
                summary="查询返回 1 行",
                success=True,
            )
        ]
    )
    executor = AgentExecutor(
        agent=FakeAgent([valid_output()]),
        publisher=publisher,
        validator=AnalysisOutputValidator(),
        max_corrections=0,
    )

    result = await executor.execute(
        AgentRuntimeContext("user_1", "conv_1", "task_1"),
        [{"role": "user", "content": "分析问题"}],
        state,
    )

    assert result.problem_definition == "为什么订单量下降"
    assert any(event["type"] == "message_delta" for _, event in publisher.events)


@pytest.mark.asyncio
async def test_executor_retries_on_validation_error():
    publisher = FakePublisher()
    agent = FakeAgent([valid_output("fake"), valid_output()])
    executor = AgentExecutor(
        agent=agent,
        publisher=publisher,
        validator=AnalysisOutputValidator(),
        max_corrections=1,
    )
    state = AnalysisExecutionState(
        tool_results=[
            ToolCallRecord(
                tool_name="sql_query",
                source_name="business.db",
                summary="查询返回 1 行",
                success=True,
            )
        ]
    )

    result = await executor.execute(
        AgentRuntimeContext("user_1", "conv_1", "task_1"),
        [{"role": "user", "content": "分析问题"}],
        state,
    )

    assert result.evidence_list[0].source_name == "business.db"
    assert agent.calls == 2


def test_factory_requires_api_key(monkeypatch):
    from app.analysis.agent import factory

    monkeypatch.setattr(
        factory,
        "get_settings",
        lambda: SimpleNamespace(deepseek_api_key=""),
    )

    with pytest.raises(RuntimeError):
        create_model()


def test_create_agent_with_dummy_model():
    from langchain_deepseek import ChatDeepSeek

    from app.analysis.agent.factory import create_analysis_agent

    runtime = AgentRuntimeContext("user_1", "conv_1", "task_1")
    executor = ToolExecutor(
        runtime,
        AnalysisExecutionState(),
        SqlQueryTool("missing.db", {"orders"}),
        TextSearchTool("missing.db"),
        publisher=FakePublisher(),
    )
    model = ChatDeepSeek(
        model="deepseek-chat",
        api_key="test-key",
        api_base="https://api.deepseek.com",
        temperature=0,
    )

    agent = create_analysis_agent(executor, model=model)

    assert agent is not None


@pytest.mark.asyncio
async def test_tool_executor_persists_messages_and_logs(db_session, business_db):
    owner, conversation, task = await create_owner_conversation_task(
        db_session, "tool"
    )
    runtime = AgentRuntimeContext(owner.id, conversation.id, task.id)
    state = AnalysisExecutionState()
    publisher = FakePublisher()
    executor = ToolExecutor(
        runtime,
        state,
        SqlQueryTool(business_db, {"orders"}, max_rows=10, timeout_seconds=2),
        TextSearchTool(business_db),
        publisher=publisher,
    )

    payload = json.loads(
        await executor.execute("sql_query", {"sql": "SELECT * FROM orders"})
    )

    assert payload["success"] is True
    assert len(state.tool_results) == 1

    async with SessionLocal() as session:
        messages = (
            await session.execute(
                select(Message).where(Message.conversation_id == conversation.id)
            )
        ).scalars().all()
        logs = (
            await session.execute(
                select(TaskLog).where(TaskLog.task_id == task.id)
            )
        ).scalars().all()

    assert any(message.tool_name == "sql_query" for message in messages)
    assert any("sql_query" in log.log_content for log in logs)
    assert any(event["type"] == "tool_start" for _, event in publisher.events)
    assert any(event["type"] == "tool_finish" for _, event in publisher.events)


@pytest.mark.asyncio
async def test_context_compiler_includes_summary_and_input(db_session):
    owner = await AuthService(db_session).upsert_user(
        AuthUserProfile(
            external_user_id="m07-context-owner",
            username="m07-context-owner",
            display_name="Owner",
        )
    )
    conversation = await ConversationService(db_session).create(owner.id, "上下文")
    message_service = MessageService(db_session)
    await message_service.append(owner.id, conversation.id, "user", "第一问")
    await message_service.append(owner.id, conversation.id, "assistant", "第一答")

    db_session.add(
        ContextSummary(
            conversation_id=conversation.id,
            start_seq_no=1,
            end_seq_no=2,
            summary_text="之前讨论过价格",
        )
    )
    await db_session.commit()

    compiled = await ContextCompiler(db_session).compile(
        owner.id, conversation.id, "第二问"
    )

    assert compiled[0]["role"] == "system"
    assert "之前讨论过价格" in compiled[0]["content"]
    assert compiled[-1] == {"role": "user", "content": "第二问"}
