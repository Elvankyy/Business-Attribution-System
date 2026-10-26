from fastapi import APIRouter, HTTPException, status

from app.analysis.coordinator import analysis_coordinator
from app.analysis.schemas import (
    TaskListItem,
    TaskLogResponse,
    TaskStatusResponse,
)
from app.analysis.service import AnalysisTaskService, TaskNotFound
from app.core.dependencies import CurrentUserDep, SessionDep
from app.core.models import AnalysisTask
from app.workspace.service import ConversationNotFound

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _to_response(task: AnalysisTask) -> TaskStatusResponse:
    return TaskStatusResponse(
        task_id=task.id,
        task_status=task.task_status,
        current_step=task.current_step,
        started_at=task.started_at,
        finished_at=task.finished_at,
        error_message=task.error_message,
    )


@router.get("", response_model=list[TaskListItem])
async def list_tasks(
    conversation_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[TaskListItem]:
    service = AnalysisTaskService(session)
    try:
        tasks = await service.list_for_conversation(
            current_user.id, conversation_id
        )
    except ConversationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在或无权访问",
        ) from exc

    result_ids = await service.result_ids_for_tasks(
        [task.id for task in tasks]
    )
    return [
        TaskListItem(
            task_id=task.id,
            task_status=task.task_status,
            current_step=task.current_step,
            input_text=task.input_text,
            started_at=task.started_at,
            finished_at=task.finished_at,
            error_message=task.error_message,
            result_id=result_ids.get(task.id),
        )
        for task in tasks
    ]


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    task_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> TaskStatusResponse:
    task = await AnalysisTaskService(session).get_for_user(task_id, current_user.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问",
        )
    return _to_response(task)


@router.get("/{task_id}/logs", response_model=list[TaskLogResponse])
async def list_task_logs(
    task_id: str,
    current_user: CurrentUserDep,
    session: SessionDep,
) -> list[TaskLogResponse]:
    try:
        logs = await AnalysisTaskService(session).list_logs(
            task_id, current_user.id
        )
    except TaskNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问",
        ) from exc

    return [
        TaskLogResponse(
            log_level=log.log_level,
            log_type=log.log_type,
            log_content=log.log_content,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.post("/{task_id}/cancel", response_model=TaskStatusResponse)
async def cancel_task(
    task_id: str,
    current_user: CurrentUserDep,
) -> TaskStatusResponse:
    try:
        task = await analysis_coordinator.cancel(task_id, current_user.id)
    except TaskNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或无权访问",
        ) from exc
    return _to_response(task)
