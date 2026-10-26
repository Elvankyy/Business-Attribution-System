from typing import Any
from uuid import uuid4

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.tools import tool

from app.analysis.agent.output import AnalysisOutput
from app.analysis.agent.prompt import SYSTEM_PROMPT
from app.analysis.harness.tools import ToolExecutor
from app.core.config import get_settings


def create_model():
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY")

    from langchain_deepseek import ChatDeepSeek

    base_url = settings.deepseek_base_url.rstrip("/")
    default_headers: dict[str, str] = {}
    extra_body: dict[str, Any] = {}
    if "opencode.ai" in base_url:
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        default_headers["x-opencode-session"] = f"bas-{uuid4().hex}"
        extra_body["thinking"] = {"type": "disabled"}

    return ChatDeepSeek(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        api_base=base_url,
        temperature=0,
        request_timeout=settings.llm_timeout_seconds,
        max_retries=1,
        default_headers=default_headers,
        extra_body=extra_body,
        model_kwargs={"parallel_tool_calls": False},
    )


def build_tools(tool_executor: ToolExecutor) -> list[Any]:
    @tool
    async def sql_query(sql: str) -> str:
        """查询业务数据库。仅允许 SELECT，表必须在白名单内，结果自动限制行数。"""
        return await tool_executor.execute("sql_query", {"sql": sql})

    @tool
    async def text_search(query: str) -> str:
        """在文档中做关键词检索，返回来源和正文片段。"""
        return await tool_executor.execute("text_search", {"query": query})

    return [sql_query, text_search]


def create_analysis_agent(tool_executor: ToolExecutor, model: Any = None):
    settings = get_settings()
    schema_hint = tool_executor.sql_tool.schema_summary()
    system_prompt = SYSTEM_PROMPT
    if schema_hint:
        system_prompt = (
            f"{SYSTEM_PROMPT}\n\n可用业务表与字段（只能使用这些表）：\n{schema_hint}"
        )

    return create_agent(
        model=model or create_model(),
        tools=build_tools(tool_executor),
        system_prompt=system_prompt,
        response_format=ToolStrategy(AnalysisOutput),
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="sql_query",
                run_limit=settings.agent_max_tool_calls,
            ),
            ToolCallLimitMiddleware(tool_name="text_search", run_limit=3),
        ],
        name="经营归因分析",
    )
