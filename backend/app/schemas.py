from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User prompt to process")
    provider: str = Field(default="openai", description="Target model provider: openai, anthropic, gemini, or cometai")
    model: Optional[str] = Field(default=None, description="Specific model ID override")
    prompt_version: str = Field(default="v1", description="Prompt template version: v1 (concise) or v2 (policy-grounded)")
    enable_pii_redaction: bool = Field(default=True, description="Whether to enforce pre-inference FERPA/PII scrubbing")


class RedactedEntity(BaseModel):
    entity_type: str = Field(..., description="Type of entity: UTD_ID, SSN, EMAIL, or PHONE")
    start: int = Field(..., description="Start character offset in original text")
    end: int = Field(..., description="End character offset in original text")
    text: str = Field(..., description="Original raw entity value")


class PrivacyReport(BaseModel):
    original_text: str
    sanitized_text: str
    redacted_count: int
    entities: List[RedactedEntity] = Field(default_factory=list)


class TelemetryMetrics(BaseModel):
    request_id: str
    timestamp: str
    model_used: str
    prompt_version: str
    ttft_ms: float
    total_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    redacted_count: int
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    requested_model: Optional[str] = None
    mcp_tools_used: List[str] = Field(default_factory=list)


class MetricsSummaryResponse(BaseModel):
    total_requests: int = 0
    avg_ttft_ms: float = 0.0
    avg_total_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_pii_redacted: int = 0
    fallback_count: int = 0
    recent_requests: List[Dict[str, Any]] = Field(default_factory=list)
