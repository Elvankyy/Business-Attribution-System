from datetime import datetime

from pydantic import BaseModel

from app.analysis.agent.output import Evidence, KeyMetric


class TaskStatusResponse(BaseModel):
    task_id: str
    task_status: str
    current_step: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None


class TaskListItem(BaseModel):
    task_id: str
    task_status: str
    current_step: str | None
    input_text: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    result_id: str | None


class TaskLogResponse(BaseModel):
    log_level: str
    log_type: str
    log_content: str
    created_at: datetime


class ResultResponse(BaseModel):
    task_id: str
    problem_definition: str
    key_metrics: list[KeyMetric]
    evidence_list: list[Evidence]
    conclusion_text: str
    missing_data_text: str
    next_action_text: str
