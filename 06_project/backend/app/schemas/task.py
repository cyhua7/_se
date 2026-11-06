from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskTriggerRequest(BaseModel):
    params: dict[str, Any] | None = None


class DynamicTaskRequest(BaseModel):
    task_name: str = Field(min_length=1, max_length=32)
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("task_name")
    @classmethod
    def validate_task_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("task_name 不可為空白")
        if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value):
            raise ValueError("task_name 不可包含控制字元")
        return value


class TaskDefinitionResponse(BaseModel):
    name: str
    label: str
    description: str
    params_hint: dict[str, Any] = Field(default_factory=dict)


class TaskLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    log_level: str = Field(validation_alias="level")
    message: str
    created_at: datetime


class TaskRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    task_name: str = Field(validation_alias="task_type")
    status: str
    progress: int
    result_summary: dict[str, Any] | None = Field(default=None, validation_alias="result")
    message: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    logs: list[TaskLogResponse] = Field(default_factory=list)


class TaskHistoryListResponse(BaseModel):
    total: int
    items: list[TaskRunResponse]
