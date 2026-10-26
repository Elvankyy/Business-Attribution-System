from datetime import datetime

from pydantic import BaseModel


class ReloadResponse(BaseModel):
    status: str
    message: str


class ConfigItem(BaseModel):
    config_key: str
    config_value: str
    config_group: str
    updated_at: datetime


class TaskLogItem(BaseModel):
    task_id: str
    log_level: str
    log_type: str
    log_content: str
    created_at: datetime


class AdminTaskItem(BaseModel):
    task_id: str
    conversation_id: str
    conversation_title: str | None
    user_id: str
    username: str
    display_name: str | None
    task_status: str
    current_step: str | None
    input_text: str
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    result_id: str | None
