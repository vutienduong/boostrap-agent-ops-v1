from datetime import datetime
from pydantic import BaseModel


class EventContext(BaseModel):
    trace_id: str | None = None
    run_id: str
    span_id: str | None = None


class EventSDK(BaseModel):
    name: str
    version: str


class EventProject(BaseModel):
    id: str
    environment: str | None = None


class IngestEvent(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    event_type: str
    timestamp: datetime
    project: EventProject
    sdk: EventSDK
    context: EventContext
    payload: dict


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = []


class SpanResponse(BaseModel):
    id: str
    run_id: str
    parent_span_id: str | None
    type: str
    name: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    status: str
    model: str | None
    tokens_prompt: int
    tokens_completion: int
    cost_usd: float
    input_json: dict | None
    output_json: dict | None
    error_json: dict | None


class RunSummary(BaseModel):
    id: str
    project_id: str
    name: str | None
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_ms: int | None
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost_usd: float
    tags: dict | None


class RunDetail(RunSummary):
    spans: list[SpanResponse] = []
    input_json: dict | None = None
    output_json: dict | None = None


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    cursor: str | None = None


class CostByDay(BaseModel):
    date: str  # YYYY-MM-DD
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    run_count: int


class CostByModel(BaseModel):
    model: str
    cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    span_count: int


class CostMetricsResponse(BaseModel):
    total_cost_usd: float
    total_prompt_tokens: int
    total_completion_tokens: int
    by_day: list[CostByDay] = []
    by_model: list[CostByModel] = []


class PromptVersionCreate(BaseModel):
    key: str
    version: str
    content: str
    meta: dict | None = None


class PromptVersionResponse(BaseModel):
    id: str
    project_id: str
    key: str
    version: str
    content: str
    meta: dict | None
    created_at: datetime


class PromptVersionListResponse(BaseModel):
    versions: list[PromptVersionResponse]
