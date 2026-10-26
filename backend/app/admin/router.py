from fastapi import APIRouter

from app.admin.schemas import AdminTaskItem, ConfigItem, ReloadResponse, TaskLogItem
from app.admin.service import ConfigService
from app.core.dependencies import AdminUserDep, SessionDep

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/reload", response_model=ReloadResponse)
async def reload_config(
    current_user: AdminUserDep,
    session: SessionDep,
) -> ReloadResponse:
    configs = await ConfigService().reload(session)
    return ReloadResponse(
        status="ok",
        message=f"配置已重载，共 {len(configs)} 项",
    )


@router.get("/configs", response_model=list[ConfigItem])
async def list_configs(
    current_user: AdminUserDep,
    session: SessionDep,
) -> list[ConfigItem]:
    rows = await ConfigService().list_configs(session)
    return [
        ConfigItem(
            config_key=row.config_key,
            config_value=row.config_value,
            config_group=row.config_group,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/logs", response_model=list[TaskLogItem])
async def list_logs(
    current_user: AdminUserDep,
    session: SessionDep,
    task_id: str | None = None,
    log_level: str | None = None,
    limit: int = 100,
) -> list[TaskLogItem]:
    rows = await ConfigService().list_logs(
        session,
        task_id=task_id,
        log_level=log_level,
        limit=limit,
    )
    return [
        TaskLogItem(
            task_id=row.task_id,
            log_level=row.log_level,
            log_type=row.log_type,
            log_content=row.log_content,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/tasks", response_model=list[AdminTaskItem])
async def list_tasks(
    current_user: AdminUserDep,
    session: SessionDep,
    limit: int = 50,
    task_status: str | None = None,
    conversation_id: str | None = None,
) -> list[AdminTaskItem]:
    rows = await ConfigService().list_tasks(
        session,
        limit=limit,
        task_status=task_status,
        conversation_id=conversation_id,
    )
    return [AdminTaskItem(**row) for row in rows]
