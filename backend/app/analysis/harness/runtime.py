from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentRuntimeContext:
    user_id: str
    conversation_id: str
    task_id: str


@dataclass
class ToolCallRecord:
    tool_name: str
    source_name: str
    summary: str
    success: bool
    data: Any = None


@dataclass
class AnalysisExecutionState:
    tool_results: list[ToolCallRecord] = field(default_factory=list)
    current_step: str = "准备分析"
