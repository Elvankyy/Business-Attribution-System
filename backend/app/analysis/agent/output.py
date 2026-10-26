from pydantic import BaseModel, Field


class KeyMetric(BaseModel):
    metric_name: str
    metric_value: float | int | str
    metric_unit: str = ""
    metric_period: str = ""


class Evidence(BaseModel):
    source_type: str
    source_name: str
    evidence_text: str
    related_metric: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AnalysisOutput(BaseModel):
    problem_definition: str
    key_metrics: list[KeyMetric]
    evidence_list: list[Evidence]
    conclusion_text: str
    missing_data_text: str
    next_action_text: str
