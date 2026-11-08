from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ClaimType = Literal[
    "pricing",
    "api_version",
    "regulation",
    "leadership",
    "product_release",
    "other",
]

Volatility = Literal["high", "medium", "low"]

Authority = Literal["official", "reputable", "community", "unknown"]

Verdict = Literal[
    "current",
    "outdated",
    "partially_outdated",
    "unverifiable",
    "skipped",
]


class Claim(BaseModel):
    id: str
    text: str
    span_start: int
    span_end: int  # char offsets in original answer
    entity: str
    attribute: str
    claimed_value: str
    claim_type: ClaimType
    volatility: Volatility
    is_time_sensitive: bool


class Evidence(BaseModel):
    url: str
    title: str
    domain: str
    snippet: str
    published_date: Optional[str] = None
    authority: Authority
    retrieved_at: str


class ScoreBreakdown(BaseModel):
    source_authority: float = Field(..., ge=0.0, le=1.0)
    evidence_recency: float = Field(..., ge=0.0, le=1.0)
    source_agreement: float = Field(..., ge=0.0, le=1.0)
    verdict_confidence: float = Field(..., ge=0.0, le=1.0)
    conflict_penalty: float = Field(..., ge=0.0, le=1.0)


class ClaimHistoryEntry(BaseModel):
    value: str
    valid_from: Optional[str] = None
    verified_at: str


class ClaimResult(BaseModel):
    claim: Claim
    verdict: Verdict
    freshness_score: int = Field(..., ge=0, le=100)
    current_value: Optional[str] = None
    explanation: str
    evidence: List[Evidence] = Field(default_factory=list)
    breakdown: ScoreBreakdown
    history: List[ClaimHistoryEntry] = Field(default_factory=list)


class GatewayModelUsage(BaseModel):
    name: str
    calls: int


class GatewayStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    cache_hits: int
    fallbacks_triggered: int
    models_used: List[GatewayModelUsage] = Field(default_factory=list)


class VerifyOptions(BaseModel):
    rewrite: bool = False
    max_claims: int = 10


class VerifyRequest(BaseModel):
    answer: str
    options: Optional[VerifyOptions] = None


class VerifyResponse(BaseModel):
    answer: str
    results: List[ClaimResult] = Field(default_factory=list)
    overall_freshness: int = Field(..., ge=0, le=100)
    corrected_answer: Optional[str] = None
    gateway: GatewayStats
    graph_available: bool
    duration_ms: float
    timings: Optional[dict[str, float]] = None


class HealthResponse(BaseModel):
    status: str
    falkordb_reachable: bool
    bifrost_reachable: bool
    timestamp: str
    details: Optional[dict[str, str]] = None


class ClaimHistoryResponse(BaseModel):
    claim_id: str
    history: List[ClaimHistoryEntry]

