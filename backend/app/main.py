from collections import defaultdict
from contextlib import asynccontextmanager
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.graph.client import get_graph_store
from app.llm.gateway import GatewayStatsCollector, cumulative_gateway_stats
from app.pipeline.extract import extract_claims
from app.pipeline.rewrite import generate_rewritten_answer
from app.pipeline.scoring import calculate_overall_freshness
from app.pipeline.triage import triage_claims
from app.pipeline.verify import VerificationEngine
from app.schemas import (
    Claim,
    ClaimHistoryEntry,
    ClaimHistoryResponse,
    ClaimResult,
    GatewayModelUsage,
    GatewayStats,
    HealthResponse,
    ScoreBreakdown,
    VerifyRequest,
    VerifyResponse,
)

logger = logging.getLogger("api")


class SimpleRateLimiter:
    """In-memory rate limiter per IP address."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < self.window_seconds
        ]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True


rate_limiter = SimpleRateLimiter(max_requests=60, window_seconds=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup: initialize FalkorDB Cloud shared client and indexes
    store = get_graph_store()
    await store.connect()
    yield
    # App shutdown


app = FastAPI(
    title="BestBefore API",
    version="0.1.0",
    description="A best-before date for every AI answer. API for detecting outdated factual claims in LLM-generated answers, verifying against live web sources, and computing freshness shelf-life.",
    lifespan=lifespan,
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint that also probes Bifrost and FalkorDB Cloud connectivity."""
    bifrost_reachable = False
    falkordb_reachable = False
    details: dict[str, str] = {}

    # Probe Bifrost Gateway
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.BIFROST_BASE_URL.rstrip('/')}/health")
            if resp.status_code < 500:
                bifrost_reachable = True
                details["bifrost"] = f"reachable (status {resp.status_code})"
            else:
                details["bifrost"] = f"unhealthy status ({resp.status_code})"
    except Exception as exc:
        details["bifrost"] = f"unreachable: {exc.__class__.__name__}"

    # Probe FalkorDB Cloud via GraphStore
    store = get_graph_store()
    if settings.FALKORDB_HOST:
        try:
            if not store.is_available:
                await store.connect()

            if store.is_available:
                stats = await store.get_stats()
                falkordb_reachable = True
                details["falkordb"] = f"connected ({stats.get('nodes', 0)} nodes, graph: {store.graph_name})"
            else:
                details["falkordb"] = "unreachable or auth failed"
        except Exception as exc:
            details["falkordb"] = f"unreachable: {exc.__class__.__name__}"
    else:
        details["falkordb"] = "not_configured (FALKORDB_HOST missing)"

    overall_status = "ok" if (bifrost_reachable and falkordb_reachable) else "degraded"

    return HealthResponse(
        status=overall_status,
        falkordb_reachable=falkordb_reachable,
        bifrost_reachable=bifrost_reachable,
        timestamp=datetime.now(timezone.utc).isoformat(),
        details=details,
    )


@app.get("/api/gateway/stats", response_model=GatewayStats)
async def get_gateway_stats() -> GatewayStats:
    """Returns cumulative Bifrost gateway statistics across all requests."""
    return cumulative_gateway_stats.get_stats()


def get_verification_engine() -> VerificationEngine:
    return VerificationEngine()


@app.post("/api/verify", response_model=VerifyResponse)
async def verify_answer(
    request: VerifyRequest,
    raw_request: Request = None,
    response: Response = None,
    engine: Optional[VerificationEngine] = Depends(get_verification_engine),
) -> VerifyResponse:
    """Full live verification pipeline: extraction -> triage -> live search & extract -> judge."""
    t_start = time.perf_counter()
    raw_header_id = raw_request.headers.get("x-request-id") if (raw_request and hasattr(raw_request, "headers")) else None
    req_id = raw_header_id if raw_header_id else f"req-{uuid.uuid4().hex[:8]}"

    if response and hasattr(response, "headers"):
        response.headers["X-Request-ID"] = str(req_id)

    # Basic rate limiting (per client IP)
    if raw_request and hasattr(raw_request, "client") and raw_request.client:
        client_ip = raw_request.client.host
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded (60 requests/minute). Please retry shortly.",
                headers={"Retry-After": "60"},
            )

    stats_collector = GatewayStatsCollector()
    timings: Dict[str, float] = {
        "extract": 0.0,
        "triage": 0.0,
        "graph_lookup": 0.0,
        "verify": 0.0,
        "score": 0.0,
        "graph_write": 0.0,
        "rewrite": 0.0,
    }

    text = request.answer.strip()
    if not text:
        return VerifyResponse(
            answer=request.answer,
            results=[],
            overall_freshness=100,
            corrected_answer=None,
            gateway=stats_collector.get_stats(),
            graph_available=get_graph_store().is_available,
            duration_ms=round((time.perf_counter() - t_start) * 1000, 2),
            timings=timings,
        )

    # 1. Extraction: extract atomic claims with verified spans
    t0 = time.perf_counter()
    extracted = await extract_claims(text, stats_collector=stats_collector)
    timings["extract"] = round((time.perf_counter() - t0) * 1000, 2)
    logger.info("[%s] Extracted %d claims (%.2fms)", req_id, len(extracted), timings["extract"])

    # 2. Triage: filter and prioritize claims by volatility & domain
    t0 = time.perf_counter()
    triaged = triage_claims(extracted, options=request.options)
    timings["triage"] = round((time.perf_counter() - t0) * 1000, 2)
    logger.info("[%s] Triaged to %d claims (%.2fms)", req_id, len(triaged), timings["triage"])

    # 3. Live Verification: search, extract, authority classification, judge, score, and graph write
    verification_engine = (
        engine if isinstance(engine, VerificationEngine) else VerificationEngine()
    )
    claim_results = await verification_engine.verify_claims(
        triaged, stats_collector=stats_collector, timings=timings
    )

    overall_freshness = calculate_overall_freshness(claim_results)

    # 4. Rewrite / corrected answer generation if requested
    corrected_answer = None
    if request.options and request.options.rewrite:
        t0 = time.perf_counter()
        corrected_answer = await generate_rewritten_answer(
            original_answer=request.answer,
            claim_results=claim_results,
            gateway=verification_engine.gateway,
            stats_collector=stats_collector,
        )
        timings["rewrite"] = round((time.perf_counter() - t0) * 1000, 2)
        logger.info("[%s] Rewrite generated (%.2fms)", req_id, timings["rewrite"])

    # Round all accumulated timings
    for k in timings:
        timings[k] = round(timings[k], 2)

    req_gateway_stats = stats_collector.get_stats()
    cumulative_gateway_stats.record_request_stats(req_gateway_stats)

    duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
    store = get_graph_store()

    logger.info(
        "[%s] Completed verification: Freshness=%d/100, Claims=%d, Duration=%.2fms",
        req_id,
        overall_freshness,
        len(claim_results),
        duration_ms,
    )

    return VerifyResponse(
        answer=request.answer,
        results=claim_results,
        overall_freshness=overall_freshness,
        corrected_answer=corrected_answer,
        gateway=req_gateway_stats,
        graph_available=store.is_available,
        duration_ms=duration_ms,
        timings=timings,
    )


@app.get("/api/claims/{claim_id}/history", response_model=ClaimHistoryResponse)
async def get_claim_history(claim_id: str) -> ClaimHistoryResponse:
    """Endpoint for retrieving temporal history of a verified claim."""
    if not claim_id:
        raise HTTPException(status_code=400, detail="Claim ID required")

    store = get_graph_store()
    if not store.is_available:
        await store.connect()

    history = []
    if store.is_available:
        try:
            history = await store.get_claim_history_by_id(claim_id)
        except Exception:
            history = []

    if not history:
        # Fallback placeholder if not found in graph
        history = [
            ClaimHistoryEntry(
                value="Initial verified value",
                valid_from=None,
                verified_at=datetime.now(timezone.utc).isoformat(),
            )
        ]

    return ClaimHistoryResponse(
        claim_id=claim_id,
        history=history,
    )


class SingleClaimVerifyRequest(BaseModel):
    claim: Claim


@app.post("/api/claims/verify-single", response_model=ClaimResult)
async def verify_single_claim_endpoint(
    req: SingleClaimVerifyRequest,
    engine: Optional[VerificationEngine] = Depends(get_verification_engine),
) -> ClaimResult:
    """Endpoint to re-verify an individual claim (e.g. on user retry)."""
    verification_engine = (
        engine if isinstance(engine, VerificationEngine) else VerificationEngine()
    )
    stats_collector = GatewayStatsCollector()
    return await verification_engine.verify_single_claim(
        req.claim, stats_collector=stats_collector
    )


@app.post("/api/verify/stream")
async def verify_answer_stream(
    request: VerifyRequest,
    raw_request: Request = None,
    engine: Optional[VerificationEngine] = Depends(get_verification_engine),
):
    """Server-Sent Events streaming endpoint emitting real-time stage progress,
    progressive claim results, and final complete response.
    """
    raw_header_id = raw_request.headers.get("x-request-id") if (raw_request and hasattr(raw_request, "headers")) else None
    req_id = raw_header_id if raw_header_id else f"req-{uuid.uuid4().hex[:8]}"

    if raw_request and hasattr(raw_request, "client") and raw_request.client:
        client_ip = raw_request.client.host
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please retry shortly.",
                headers={"Retry-After": "60"},
            )

    verification_engine = (
        engine if isinstance(engine, VerificationEngine) else VerificationEngine()
    )

    async def sse_generator():
        t_start = time.perf_counter()
        stats_collector = GatewayStatsCollector()
        timings: Dict[str, float] = {
            "extract": 0.0,
            "triage": 0.0,
            "graph_lookup": 0.0,
            "verify": 0.0,
            "score": 0.0,
            "graph_write": 0.0,
            "rewrite": 0.0,
        }

        text = request.answer.strip()
        if not text:
            empty_res = VerifyResponse(
                answer=request.answer,
                results=[],
                overall_freshness=100,
                corrected_answer=None,
                gateway=stats_collector.get_stats(),
                graph_available=get_graph_store().is_available,
                duration_ms=0.0,
                timings=timings,
            )
            yield f"event: complete\ndata: {empty_res.model_dump_json()}\n\n"
            return

        # 1. Extraction
        yield f"event: stage\ndata: {json.dumps({'stage': 'extract', 'step': 0, 'message': 'Extracting atomic claims...'})}\n\n"
        t0 = time.perf_counter()
        extracted = await extract_claims(text, stats_collector=stats_collector)
        timings["extract"] = round((time.perf_counter() - t0) * 1000, 2)

        # 2. Triage
        yield f"event: stage\ndata: {json.dumps({'stage': 'triage', 'step': 1, 'message': f'Identified {len(extracted)} claims. Triaging volatility...'})}\n\n"
        t0 = time.perf_counter()
        triaged = triage_claims(extracted, options=request.options)
        timings["triage"] = round((time.perf_counter() - t0) * 1000, 2)

        # 3. Progressive Claim Verification
        yield f"event: stage\ndata: {json.dumps({'stage': 'search', 'step': 2, 'message': f'Verifying {len(triaged)} claims against live web & knowledge graph...'})}\n\n"
        claim_results: List[ClaimResult] = []

        for idx, claim in enumerate(triaged, start=1):
            yield f"event: stage\ndata: {json.dumps({'stage': 'judge', 'step': 3, 'message': f'Judging claim {idx}/{len(triaged)}: {claim.entity} ({claim.attribute})...'})}\n\n"
            res = await verification_engine.verify_single_claim(
                claim, stats_collector=stats_collector, timings=timings
            )
            claim_results.append(res)
            # Emit progressive claim result
            yield f"event: claim\ndata: {res.model_dump_json()}\n\n"

        # 4. Scoring
        yield f"event: stage\ndata: {json.dumps({'stage': 'score', 'step': 4, 'message': 'Deriving deterministic freshness scores...'})}\n\n"
        overall_freshness = calculate_overall_freshness(claim_results)

        # 5. Rewrite
        corrected_answer = None
        if request.options and request.options.rewrite:
            yield f"event: stage\ndata: {json.dumps({'stage': 'rewrite', 'step': 5, 'message': 'Generating factual rewrite with inline citations...'})}\n\n"
            t0 = time.perf_counter()
            corrected_answer = await generate_rewritten_answer(
                original_answer=request.answer,
                claim_results=claim_results,
                gateway=verification_engine.gateway,
                stats_collector=stats_collector,
            )
            timings["rewrite"] = round((time.perf_counter() - t0) * 1000, 2)

        for k in timings:
            timings[k] = round(timings[k], 2)

        req_gateway_stats = stats_collector.get_stats()
        cumulative_gateway_stats.record_request_stats(req_gateway_stats)
        duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        store = get_graph_store()

        final_resp = VerifyResponse(
            answer=request.answer,
            results=claim_results,
            overall_freshness=overall_freshness,
            corrected_answer=corrected_answer,
            gateway=req_gateway_stats,
            graph_available=store.is_available,
            duration_ms=duration_ms,
            timings=timings,
        )
        yield f"event: complete\ndata: {final_resp.model_dump_json()}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": str(req_id),
        },
    )
