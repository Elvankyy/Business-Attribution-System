import asyncio
import logging
from typing import Any, Protocol

from app.analysis.agent.output import AnalysisOutput
from app.analysis.service import (
    TERMINAL_TASK_STATUSES,
    AnalysisResultService,
    AnalysisTaskService,
    ContextSummaryService,
)
from app.core import events
from app.core.database import SessionLocal
from app.core.models import get_utcnow
from app.core.realtime import EventPublisher, event_publisher
from app.workspace.service import MessageService

logger = logging.getLogger(__name__)


class AnalysisRunner(Protocol):
    async def run(
        self,
        *,
        task_id: str,
        user_id: str,
        conversation_id: str,
        input_text: str,
    ) -> Any: ...


class AnalysisCoordinator:
    def __init__(
        self,
        *,
        runner: AnalysisRunner | None = None,
        publisher: EventPublisher | None = None,
    ) -> None:
        self.runner = runner
        self.publisher = publisher or event_publisher
        self._tasks: dict[str, asyncio.Task] = {}

    async def start_analysis(
        self, user_id: str, conversation_id: str, input_text: str
    ):
        async with SessionLocal() as session:
            task = await AnalysisTaskService(session).create(
                user_id, conversation_id, input_text
            )
        handle = asyncio.create_task(
            self._run(task.id, user_id, conversation_id, input_text)
        )
        self._tasks[task.id] = handle
        return task

    async def _run(
        self,
        task_id: str,
        user_id: str,
        conversation_id: str,
        input_text: str,
    ) -> None:
        try:
            async with SessionLocal() as session:
                service = AnalysisTaskService(session)
                task = await service.get_by_id(task_id)
                if task is None or task.task_status in TERMINAL_TASK_STATUSES:
                    return

                await service.update_status(task, "running", current_step="准备分析")
                await self.publisher.publish(
                    conversation_id, events.message_start(task_id, conversation_id)
                )
                await self.publisher.publish(
                    conversation_id,
                    events.task_status(task_id, "running", "准备分析"),
                )

                if self.runner is None:
                    raise RuntimeError("分析模块待接入")
                output = await self.runner.run(
                    task_id=task_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    input_text=input_text,
                )

                if isinstance(output, AnalysisOutput):
                    result = await AnalysisResultService(session).save_output(
                        task, output
                    )
                    await MessageService(session).append(
                        user_id,
                        conversation_id,
                        "assistant",
                        output.conclusion_text,
                        message_type="analysis",
                    )
                    try:
                        await ContextSummaryService(session).compress(
                            conversation_id
                        )
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("上下文摘要压缩失败：%s", exc)
                    await self.publisher.publish(
                        conversation_id,
                        events.result_ready(task_id, result.id),
                    )

                await service.update_status(task, "success", current_step="完成")
                await self.publisher.publish(
                    conversation_id, events.task_status(task_id, "success", "完成")
                )
                await self.publisher.publish(
                    conversation_id,
                    events.done(task_id, task.finished_at or get_utcnow()),
                )
        except asyncio.CancelledError:
            async with SessionLocal() as session:
                service = AnalysisTaskService(session)
                task = await service.get_by_id(task_id)
                if task is not None and task.task_status not in TERMINAL_TASK_STATUSES:
                    await service.update_status(
                        task, "cancelled", current_step="已取消"
                    )
                    await self.publisher.publish(
                        conversation_id,
                        events.task_status(task_id, "cancelled", "已取消"),
                    )
                    await self.publisher.publish(
                        conversation_id,
                        events.done(task_id, task.finished_at or get_utcnow()),
                    )
            return
        except Exception as exc:  # noqa: BLE001
            async with SessionLocal() as session:
                service = AnalysisTaskService(session)
                task = await service.get_by_id(task_id)
                if task is not None and task.task_status not in TERMINAL_TASK_STATUSES:
                    await service.update_status(
                        task,
                        "failed",
                        current_step="失败",
                        error_message=str(exc),
                    )
                    await self.publisher.publish(
                        conversation_id,
                        events.task_status(task_id, "failed", "失败"),
                    )
                    await self.publisher.publish(
                        conversation_id, events.error(task_id, str(exc))
                    )
                    await self.publisher.publish(
                        conversation_id,
                        events.done(task_id, task.finished_at or get_utcnow()),
                    )
        finally:
            self._tasks.pop(task_id, None)

    async def cancel(self, task_id: str, user_id: str):
        async with SessionLocal() as session:
            task = await AnalysisTaskService(session).cancel(task_id, user_id)
            conversation_id = task.conversation_id
            task_status_value = task.task_status
            finished_at = task.finished_at

        handle = self._tasks.get(task_id)
        if handle is not None and not handle.done():
            handle.cancel()

        if task_status_value == "cancelled":
            await self.publisher.publish(
                conversation_id,
                events.task_status(task_id, "cancelled", "已取消"),
            )
            await self.publisher.publish(
                conversation_id,
                events.done(task_id, finished_at or get_utcnow()),
            )
        return task

    async def recover_stale_tasks(self) -> int:
        async with SessionLocal() as session:
            return await AnalysisTaskService(session).mark_running_as_failed()


analysis_coordinator = AnalysisCoordinator()
