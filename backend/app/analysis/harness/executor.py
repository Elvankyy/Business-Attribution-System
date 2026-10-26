from typing import Any

from app.analysis.agent.factory import create_analysis_agent
from app.analysis.agent.output import AnalysisOutput
from app.analysis.harness.context import ContextCompiler
from app.analysis.harness.runtime import (
    AgentRuntimeContext,
    AnalysisExecutionState,
)
from app.analysis.harness.tools import (
    SqlQueryTool,
    TextSearchTool,
    ToolExecutor,
    sqlite_path_from_url,
)
from app.analysis.harness.validator import AnalysisOutputValidator
from app.core import events
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.realtime import EventPublisher, event_publisher


class AnalysisExecutionError(Exception):
    pass


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def _extract_structured(output: Any) -> Any:
    if output is None:
        return None
    if isinstance(output, AnalysisOutput):
        return output
    if isinstance(output, dict):
        candidate = output.get("structured_response")
        if candidate is not None:
            return candidate
        nested = output.get("output")
        if nested is not None and nested is not output:
            return _extract_structured(nested)
        return None
    return getattr(output, "structured_response", None)


class AgentExecutor:
    def __init__(
        self,
        *,
        agent: Any,
        publisher: EventPublisher,
        validator: AnalysisOutputValidator,
        max_corrections: int = 2,
    ) -> None:
        self.agent = agent
        self.publisher = publisher
        self.validator = validator
        self.max_corrections = max_corrections

    async def execute(
        self,
        runtime: AgentRuntimeContext,
        messages: list[dict[str, str]],
        state: AnalysisExecutionState,
    ) -> AnalysisOutput:
        errors: list[str] = []
        for _ in range(self.max_corrections + 1):
            output = await self._stream_agent(runtime, messages)
            errors = self.validator.validate(output, state.tool_results)
            if not errors:
                return output
            messages = [
                *messages,
                {
                    "role": "system",
                    "content": self.validator.correction_message(errors),
                },
            ]

        raise AnalysisExecutionError("；".join(errors))

    async def _stream_agent(
        self, runtime: AgentRuntimeContext, messages: list[dict[str, str]]
    ) -> AnalysisOutput:
        structured: Any = None
        async for event in self.agent.astream_events(
            {"messages": messages},
            version="v2",
            config={"recursion_limit": 50},
        ):
            event_type = event.get("event")
            if event_type == "on_chat_model_stream":
                text = _chunk_text(event.get("data", {}).get("chunk"))
                if text:
                    await self.publisher.publish(
                        runtime.conversation_id,
                        events.message_delta(runtime.task_id, text),
                    )
            elif event_type == "on_chain_end":
                candidate = _extract_structured(
                    event.get("data", {}).get("output")
                )
                if candidate is not None:
                    structured = candidate

        if structured is None:
            raise AnalysisExecutionError("模型未返回结构化结果")
        if isinstance(structured, AnalysisOutput):
            return structured
        return AnalysisOutput.model_validate(structured)


class LangChainAnalysisRunner:
    def __init__(self, *, publisher: EventPublisher | None = None) -> None:
        self.publisher = publisher or event_publisher

    async def run(
        self,
        *,
        task_id: str,
        user_id: str,
        conversation_id: str,
        input_text: str,
    ) -> AnalysisOutput:
        settings = get_settings()
        runtime = AgentRuntimeContext(
            user_id=user_id,
            conversation_id=conversation_id,
            task_id=task_id,
        )
        state = AnalysisExecutionState()
        db_path = sqlite_path_from_url(settings.business_database_url)
        tool_executor = ToolExecutor(
            runtime,
            state,
            SqlQueryTool(
                db_path=db_path,
                allowed_tables=set(settings.sql_allowed_tables),
                max_rows=settings.sql_max_rows,
                timeout_seconds=settings.sql_query_timeout_seconds,
            ),
            TextSearchTool(db_path=db_path, max_rows=20),
            publisher=self.publisher,
        )

        async with SessionLocal() as session:
            messages = await ContextCompiler(session).compile(
                user_id, conversation_id, input_text
            )

        agent = create_analysis_agent(tool_executor)
        executor = AgentExecutor(
            agent=agent,
            publisher=self.publisher,
            validator=AnalysisOutputValidator(),
            max_corrections=settings.agent_max_corrections,
        )
        return await executor.execute(runtime, messages, state)
