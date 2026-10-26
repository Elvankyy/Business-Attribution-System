from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import (
    AnalysisResult,
    AnalysisTask,
    Conversation,
    SystemConfig,
    TaskLog,
    User,
)

_runtime_configs: dict[str, str] = {}


class ConfigService:
    async def reload(self, session: AsyncSession) -> dict[str, str]:
        get_settings.cache_clear()
        result = await session.execute(
            select(SystemConfig).order_by(
                SystemConfig.config_group, SystemConfig.config_key
            )
        )
        rows = list(result.scalars().all())

        global _runtime_configs
        _runtime_configs = {
            row.config_key: row.config_value for row in rows
        }
        return dict(_runtime_configs)

    async def list_configs(self, session: AsyncSession) -> list[SystemConfig]:
        result = await session.execute(
            select(SystemConfig).order_by(
                SystemConfig.config_group, SystemConfig.config_key
            )
        )
        return list(result.scalars().all())

    def get_all(self) -> dict[str, str]:
        return dict(_runtime_configs)

    def get(self, key: str, default: str | None = None) -> str | None:
        return _runtime_configs.get(key, default)

    async def list_logs(
        self,
        session: AsyncSession,
        *,
        task_id: str | None = None,
        log_level: str | None = None,
        limit: int = 100,
    ) -> list[TaskLog]:
        statement = select(TaskLog).order_by(TaskLog.created_at.desc())
        if task_id:
            statement = statement.where(TaskLog.task_id == task_id)
        if log_level:
            statement = statement.where(TaskLog.log_level == log_level)
        statement = statement.limit(min(max(limit, 1), 500))
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def list_tasks(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
        task_status: str | None = None,
        conversation_id: str | None = None,
    ) -> list[dict]:
        statement = (
            select(
                AnalysisTask,
                Conversation.title,
                User.username,
                User.display_name,
                AnalysisResult.id,
            )
            .join(Conversation, Conversation.id == AnalysisTask.conversation_id)
            .join(User, User.id == AnalysisTask.user_id)
            .outerjoin(AnalysisResult, AnalysisResult.task_id == AnalysisTask.id)
            .order_by(AnalysisTask.started_at.desc(), AnalysisTask.id.desc())
            .limit(min(max(limit, 1), 200))
        )
        if task_status:
            statement = statement.where(AnalysisTask.task_status == task_status)
        if conversation_id:
            statement = statement.where(
                AnalysisTask.conversation_id == conversation_id
            )

        result = await session.execute(statement)
        return [
            {
                "task_id": task.id,
                "conversation_id": task.conversation_id,
                "conversation_title": title,
                "user_id": task.user_id,
                "username": username,
                "display_name": display_name,
                "task_status": task.task_status,
                "current_step": task.current_step,
                "input_text": task.input_text,
                "started_at": task.started_at,
                "finished_at": task.finished_at,
                "error_message": task.error_message,
                "result_id": result_id,
            }
            for task, title, username, display_name, result_id in result.all()
        ]
