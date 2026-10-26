from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.agent.output import AnalysisOutput
from app.core.config import get_settings
from app.core.models import (
    AnalysisResult,
    AnalysisTask,
    ContextSummary,
    TaskLog,
    get_utcnow,
)
from app.workspace.repository import ConversationRepository, MessageRepository
from app.workspace.service import ConversationNotFound
from app.workspace.storage import conversation_dir, resolve_storage_path, safe_path

ACTIVE_TASK_STATUSES = {"queued", "running"}
TERMINAL_TASK_STATUSES = {"success", "failed", "cancelled"}
ALLOWED_TRANSITIONS = {
    "queued": {"running", "cancelled", "failed"},
    "running": {"success", "failed", "cancelled"},
    "success": set(),
    "failed": set(),
    "cancelled": set(),
}


class TaskNotFound(Exception):
    pass


class TaskAlreadyRunning(Exception):
    pass


class AnalysisTaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)

    async def create(
        self, user_id: str, conversation_id: str, input_text: str
    ) -> AnalysisTask:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        active = await self.session.execute(
            select(AnalysisTask.id)
            .where(
                AnalysisTask.conversation_id == conversation_id,
                AnalysisTask.task_status.in_(ACTIVE_TASK_STATUSES),
            )
            .limit(1)
        )
        if active.scalar_one_or_none() is not None:
            raise TaskAlreadyRunning(conversation_id)

        task = AnalysisTask(
            conversation_id=conversation_id,
            user_id=user_id,
            input_text=input_text,
            task_status="queued",
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_for_user(self, task_id: str, user_id: str) -> AnalysisTask | None:
        result = await self.session.execute(
            select(AnalysisTask).where(
                AnalysisTask.id == task_id,
                AnalysisTask.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, task_id: str) -> AnalysisTask | None:
        return await self.session.get(AnalysisTask, task_id)

    async def update_status(
        self,
        task: AnalysisTask,
        status: str,
        *,
        current_step: str | None = None,
        error_message: str | None = None,
    ) -> AnalysisTask:
        if status == task.task_status:
            if current_step is not None:
                task.current_step = current_step
            await self.session.commit()
            await self.session.refresh(task)
            return task

        allowed = ALLOWED_TRANSITIONS.get(task.task_status, set())
        if status not in allowed:
            raise ValueError(f"非法任务状态流转：{task.task_status} -> {status}")

        task.task_status = status
        if current_step is not None:
            task.current_step = current_step
        if status == "running" and task.started_at is None:
            task.started_at = get_utcnow()
        if status in TERMINAL_TASK_STATUSES:
            task.finished_at = get_utcnow()
        if error_message is not None:
            task.error_message = error_message

        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def cancel(self, task_id: str, user_id: str) -> AnalysisTask:
        task = await self.get_for_user(task_id, user_id)
        if task is None:
            raise TaskNotFound(task_id)
        if task.task_status in TERMINAL_TASK_STATUSES:
            return task
        return await self.update_status(task, "cancelled", current_step="已取消")

    async def append_log(
        self, task_id: str, log_level: str, log_type: str, log_content: str
    ) -> TaskLog:
        log = TaskLog(
            task_id=task_id,
            log_level=log_level,
            log_type=log_type,
            log_content=log_content,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log

    async def list_for_conversation(
        self, user_id: str, conversation_id: str
    ) -> list[AnalysisTask]:
        conversation = await self.conversation_repository.get_for_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise ConversationNotFound(conversation_id)

        result = await self.session.execute(
            select(AnalysisTask)
            .where(
                AnalysisTask.conversation_id == conversation_id,
                AnalysisTask.user_id == user_id,
            )
            .order_by(AnalysisTask.started_at.desc(), AnalysisTask.id.desc())
        )
        return list(result.scalars().all())

    async def result_ids_for_tasks(
        self, task_ids: list[str]
    ) -> dict[str, str]:
        if not task_ids:
            return {}
        result = await self.session.execute(
            select(AnalysisResult.task_id, AnalysisResult.id).where(
                AnalysisResult.task_id.in_(task_ids)
            )
        )
        return {
            task_id: result_id for task_id, result_id in result.all()
        }

    async def list_logs(
        self, task_id: str, user_id: str
    ) -> list[TaskLog]:
        task = await self.get_for_user(task_id, user_id)
        if task is None:
            raise TaskNotFound(task_id)

        result = await self.session.execute(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def mark_running_as_failed(self) -> int:
        result = await self.session.execute(
            update(AnalysisTask)
            .where(AnalysisTask.task_status == "running")
            .values(
                task_status="failed",
                finished_at=get_utcnow(),
                error_message="服务重启，任务中断",
            )
        )
        await self.session.commit()
        return result.rowcount or 0


class ResultNotFound(Exception):
    pass


class AnalysisResultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_output(
        self, task: AnalysisTask, output: AnalysisOutput
    ) -> AnalysisResult:
        markdown = self.build_markdown(task, output)
        result = AnalysisResult(
            task_id=task.id,
            conversation_id=task.conversation_id,
            problem_definition=output.problem_definition,
            key_metrics_json=[metric.model_dump() for metric in output.key_metrics],
            evidence_list_json=[
                evidence.model_dump() for evidence in output.evidence_list
            ],
            conclusion_text=output.conclusion_text,
            missing_data_text=output.missing_data_text,
            next_action_text=output.next_action_text,
            result_markdown=markdown,
            result_file_path=self._write_export_file(task, markdown),
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_for_user(
        self, task_id: str, user_id: str
    ) -> AnalysisResult | None:
        result = await self.session.execute(
            select(AnalysisResult)
            .join(AnalysisTask, AnalysisTask.id == AnalysisResult.task_id)
            .where(
                AnalysisResult.task_id == task_id,
                AnalysisTask.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_file_for_user(
        self, task_id: str, user_id: str
    ) -> tuple[AnalysisResult, Path]:
        result = await self.get_for_user(task_id, user_id)
        if result is None or not result.result_file_path:
            raise ResultNotFound(task_id)

        try:
            path = resolve_storage_path(result.result_file_path)
        except ValueError as exc:
            raise ResultNotFound(task_id) from exc
        if not path.exists():
            raise ResultNotFound(task_id)
        return result, path

    def build_markdown(self, task: AnalysisTask, output: AnalysisOutput) -> str:
        lines = [
            "# 经营归因分析报告",
            "",
            f"- 任务：{task.id}",
            f"- 会话：{task.conversation_id}",
            "",
            "## 问题定义",
            output.problem_definition,
            "",
            "## 关键指标",
            "| 指标 | 数值 | 单位 | 周期 |",
            "|---|---|---|---|",
        ]
        for metric in output.key_metrics:
            lines.append(
                f"| {metric.metric_name} | {metric.metric_value} | "
                f"{metric.metric_unit} | {metric.metric_period} |"
            )

        lines.extend(
            [
                "",
                "## 证据列表",
                "| 来源类型 | 来源 | 证据 | 关联指标 | 置信度 |",
                "|---|---|---|---|---|",
            ]
        )
        for evidence in output.evidence_list:
            lines.append(
                f"| {evidence.source_type} | {evidence.source_name} | "
                f"{evidence.evidence_text} | {evidence.related_metric} | "
                f"{evidence.confidence} |"
            )

        lines.extend(
            [
                "",
                "## 归因结论",
                output.conclusion_text,
                "",
                "## 待补充数据",
                output.missing_data_text,
                "",
                "## 下一步建议",
                output.next_action_text,
                "",
            ]
        )
        return "\n".join(lines)

    def _write_export_file(self, task: AnalysisTask, markdown: str) -> str:
        directory = conversation_dir(
            "exports", task.user_id, task.conversation_id
        )
        directory.mkdir(parents=True, exist_ok=True)
        path = safe_path(directory, f"result_{task.id}.md")
        path.write_text(markdown, encoding="utf-8")
        return path.relative_to(get_settings().storage_path.resolve()).as_posix()


class ContextSummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.message_repository = MessageRepository(session)

    async def compress(
        self, conversation_id: str, keep_recent: int = 10
    ) -> ContextSummary | None:
        messages = await self.message_repository.list_for_conversation(
            conversation_id
        )
        if len(messages) <= keep_recent:
            return None

        older = messages[:-keep_recent]
        last_end = await self.session.execute(
            select(func.max(ContextSummary.end_seq_no)).where(
                ContextSummary.conversation_id == conversation_id
            )
        )
        last_end_seq = last_end.scalar() or 0
        pending = [message for message in older if message.seq_no > last_end_seq]
        if not pending:
            return None

        summary_text = "\n".join(
            f"{message.role}: {message.content}"
            for message in pending
            if message.content.strip()
        )
        if not summary_text:
            return None

        summary = ContextSummary(
            conversation_id=conversation_id,
            start_seq_no=pending[0].seq_no,
            end_seq_no=pending[-1].seq_no,
            summary_text=summary_text[:4000],
        )
        self.session.add(summary)
        await self.session.commit()
        await self.session.refresh(summary)
        return summary
