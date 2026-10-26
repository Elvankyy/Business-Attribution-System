import asyncio
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.analysis.harness.runtime import (
    AgentRuntimeContext,
    AnalysisExecutionState,
    ToolCallRecord,
)
from app.analysis.service import AnalysisTaskService
from app.core import events
from app.core.database import SessionLocal
from app.core.realtime import EventPublisher, event_publisher
from app.workspace.service import MessageService

FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace)\b",
    re.IGNORECASE,
)
TABLE_PATTERN = re.compile(
    r"\b(?:from|join)\s+([`\"\[]?)([A-Za-z_][\w]*)\1",
    re.IGNORECASE,
)


def sqlite_path_from_url(url: str) -> str:
    if url.startswith("sqlite"):
        return url.split("///", 1)[-1].split("?", 1)[0]
    return url


@dataclass
class ToolResult:
    success: bool
    tool_name: str
    source_name: str
    summary: str
    data: Any = None
    error: str | None = None


class SqlQueryTool:
    def __init__(
        self,
        db_path: str,
        allowed_tables: set[str],
        max_rows: int = 200,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.db_path = db_path
        self.allowed_tables = allowed_tables
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds

    async def run(self, sql: str) -> ToolResult:
        return await asyncio.to_thread(self._run_sync, sql)

    def _run_sync(self, sql: str) -> ToolResult:
        normalized = sql.strip().rstrip(";").strip()
        if not normalized:
            return self._failure("SQL 不能为空")
        if ";" in normalized:
            return self._failure("不允许多语句")
        if "--" in normalized or "/*" in normalized:
            return self._failure("不允许 SQL 注释")
        if FORBIDDEN_SQL.search(normalized):
            return self._failure("只允许只读查询")
        if not re.match(r"^select\b", normalized, re.IGNORECASE):
            return self._failure("只允许 SELECT 查询")

        tables = {
            match[1] for match in TABLE_PATTERN.findall(normalized)
        }
        if not tables:
            return self._failure("未识别到查询表")
        if not tables <= self.allowed_tables:
            invalid = ", ".join(sorted(tables - self.allowed_tables))
            return self._failure(f"表不在白名单：{invalid}")

        path = Path(self.db_path)
        if not path.exists():
            return self._failure("业务数据库不存在")

        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=self.timeout_seconds,
        )
        deadline = time.monotonic() + self.timeout_seconds
        connection.set_progress_handler(
            lambda: 1 if time.monotonic() > deadline else 0,
            1000,
        )
        try:
            connection.execute("PRAGMA query_only=ON")
            cursor = connection.execute(
                f"SELECT * FROM ({normalized}) LIMIT ?",
                (self.max_rows,),
            )
            columns = [column[0] for column in cursor.description or []]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return ToolResult(
                success=True,
                tool_name="sql_query",
                source_name="business.db",
                summary=f"查询返回 {len(rows)} 行",
                data={"columns": columns, "rows": rows},
            )
        except sqlite3.Error as exc:
            return self._failure(f"查询失败：{exc}")
        finally:
            connection.close()

    def _failure(self, message: str) -> ToolResult:
        return ToolResult(
            success=False,
            tool_name="sql_query",
            source_name="business.db",
            summary="查询失败",
            error=message,
        )

    def schema_summary(self) -> str:
        path = Path(self.db_path)
        if not path.exists():
            return ""

        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=10,
        )
        try:
            lines: list[str] = []
            for table in sorted(self.allowed_tables):
                if table == "documents_fts":
                    continue
                rows = connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
                if not rows:
                    continue
                columns = ", ".join(f"{row[1]} {row[2]}" for row in rows)
                lines.append(f"- {table}: {columns}")
            return "\n".join(lines)
        finally:
            connection.close()


class TextSearchTool:
    def __init__(self, db_path: str, max_rows: int = 20) -> None:
        self.db_path = db_path
        self.max_rows = max_rows

    async def run(self, query: str) -> ToolResult:
        return await asyncio.to_thread(self._run_sync, query)

    def _run_sync(self, query: str) -> ToolResult:
        if not query.strip():
            return self._failure("检索词不能为空")

        path = Path(self.db_path)
        if not path.exists():
            return self._failure("业务数据库不存在")

        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=10,
        )
        try:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type IN ('table', 'view') AND name = 'documents_fts'"
            ).fetchone()
            if exists is None:
                return self._failure("文本检索表不存在")

            phrase = " ".join(
                f'"{term}"*' for term in query.split() if term
            )
            if not phrase:
                return self._failure("检索词不能为空")
            cursor = connection.execute(
                "SELECT source_name, content FROM documents_fts "
                "WHERE documents_fts MATCH ? LIMIT ?",
                (phrase, self.max_rows),
            )
            rows = [
                {"source_name": row[0], "content": row[1]}
                for row in cursor.fetchall()
            ]
            return ToolResult(
                success=True,
                tool_name="text_search",
                source_name="documents_fts",
                summary=f"检索到 {len(rows)} 条",
                data={"results": rows},
            )
        except sqlite3.Error as exc:
            return self._failure(f"检索失败：{exc}")
        finally:
            connection.close()

    def _failure(self, message: str) -> ToolResult:
        return ToolResult(
            success=False,
            tool_name="text_search",
            source_name="documents_fts",
            summary="检索失败",
            error=message,
        )


class ToolExecutor:
    def __init__(
        self,
        runtime: AgentRuntimeContext,
        state: AnalysisExecutionState,
        sql_tool: SqlQueryTool,
        text_search_tool: TextSearchTool,
        *,
        publisher: EventPublisher | None = None,
        session_factory=SessionLocal,
    ) -> None:
        self.runtime = runtime
        self.state = state
        self.sql_tool = sql_tool
        self.text_search_tool = text_search_tool
        self.publisher = publisher or event_publisher
        self.session_factory = session_factory

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        await self.publisher.publish(
            self.runtime.conversation_id,
            events.tool_start(self.runtime.task_id, tool_name),
        )
        started = time.monotonic()

        if tool_name == "sql_query":
            result = await self.sql_tool.run(str(arguments.get("sql", "")))
        elif tool_name == "text_search":
            result = await self.text_search_tool.run(
                str(arguments.get("query", ""))
            )
        else:
            result = ToolResult(
                success=False,
                tool_name=tool_name,
                source_name=tool_name,
                summary="未知工具",
                error=f"未知工具：{tool_name}",
            )

        elapsed_ms = int((time.monotonic() - started) * 1000)
        summary = result.summary if result.success else (result.error or "工具执行失败")
        self.state.tool_results.append(
            ToolCallRecord(
                tool_name=tool_name,
                source_name=result.source_name,
                summary=summary,
                success=result.success,
                data=result.data,
            )
        )

        try:
            await self._persist(tool_name, result, elapsed_ms)
        except Exception as exc:  # noqa: BLE001
            summary = f"{summary}（记录失败：{exc}）"

        await self.publisher.publish(
            self.runtime.conversation_id,
            events.tool_finish(self.runtime.task_id, tool_name, summary),
        )
        return json.dumps(
            {
                "success": result.success,
                "source_name": result.source_name,
                "summary": summary,
                "data": result.data,
                "error": result.error,
            },
            ensure_ascii=False,
            default=str,
        )

    async def _persist(
        self, tool_name: str, result: ToolResult, elapsed_ms: int
    ) -> None:
        content = result.summary if result.success else (result.error or "工具执行失败")
        async with self.session_factory() as session:
            await MessageService(session).append(
                self.runtime.user_id,
                self.runtime.conversation_id,
                "tool",
                content,
                message_type="tool_call",
                tool_name=tool_name,
                tool_status="success" if result.success else "failed",
            )
            await AnalysisTaskService(session).append_log(
                self.runtime.task_id,
                "info" if result.success else "error",
                "tool",
                f"{tool_name} 耗时 {elapsed_ms}ms：{content}",
            )
