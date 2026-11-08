import json
import logging
import time
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar
import httpx
from openai import AsyncOpenAI, APIConnectionError
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.schemas import GatewayModelUsage, GatewayStats

logger = logging.getLogger("gateway")

T = TypeVar("T", bound=BaseModel)

TaskType = Literal["extract", "judge"]

# Model mapping per task (Fast model for extraction, stronger model for verification/judging)
TASK_MODELS: Dict[str, str] = {
    "extract": "groq/llama-3.1-8b-instant",
    "judge": "groq/llama-3.3-70b-versatile",
}

# Cost per million tokens (input, output) estimates in USD
MODEL_PRICING: Dict[str, tuple[float, float]] = {
    "groq/llama-3.1-8b-instant": (0.05, 0.08),
    "llama-3.1-8b-instant": (0.05, 0.08),
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimates cost in USD based on model pricing."""
    rates = MODEL_PRICING.get(model, (0.20, 0.40))
    input_cost = (prompt_tokens / 1_000_000.0) * rates[0]
    output_cost = (completion_tokens / 1_000_000.0) * rates[1]
    return input_cost + output_cost


class GatewayStatsCollector:
    """Request-scoped collector for Bifrost gateway metrics."""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.latencies_ms: List[float] = []
        self.cache_hits: int = 0
        self.fallbacks_triggered: int = 0
        self.models_call_counts: Dict[str, int] = {}

    def record_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        cache_hit: bool = False,
        fallback_used: bool = False,
    ) -> None:
        self.total_requests += 1
        tokens = prompt_tokens + completion_tokens
        self.total_tokens += tokens
        self.latencies_ms.append(latency_ms)

        if cache_hit:
            self.cache_hits += 1
        if fallback_used:
            self.fallbacks_triggered += 1

        self.models_call_counts[model] = self.models_call_counts.get(model, 0) + 1
        self.total_cost_usd += estimate_cost(model, prompt_tokens, completion_tokens)

    def record_cache_hit(self) -> None:
        """Records a cache hit from either Bifrost semantic cache or knowledge graph."""
        self.cache_hits += 1

    def record_fallback(self) -> None:
        """Records a model fallback trigger."""
        self.fallbacks_triggered += 1

    def get_stats(self) -> GatewayStats:
        avg_lat = (
            sum(self.latencies_ms) / len(self.latencies_ms)
            if self.latencies_ms
            else 0.0
        )
        models_used = [
            GatewayModelUsage(name=m, calls=c)
            for m, c in self.models_call_counts.items()
        ]
        return GatewayStats(
            total_requests=self.total_requests,
            total_tokens=self.total_tokens,
            total_cost_usd=round(self.total_cost_usd, 6),
            avg_latency_ms=round(avg_lat, 2),
            cache_hits=self.cache_hits,
            fallbacks_triggered=self.fallbacks_triggered,
            models_used=models_used,
        )


class CumulativeGatewayStats:
    """Cumulative metrics tracker across all requests since application start."""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.latencies_ms: List[float] = []
        self.cache_hits: int = 0
        self.fallbacks_triggered: int = 0
        self.models_call_counts: Dict[str, int] = {}

    def record_request_stats(self, req_stats: GatewayStats) -> None:
        self.total_requests += req_stats.total_requests
        self.total_tokens += req_stats.total_tokens
        self.total_cost_usd += req_stats.total_cost_usd
        if req_stats.avg_latency_ms > 0:
            self.latencies_ms.append(req_stats.avg_latency_ms)
        self.cache_hits += req_stats.cache_hits
        self.fallbacks_triggered += req_stats.fallbacks_triggered
        for m in req_stats.models_used:
            self.models_call_counts[m.name] = (
                self.models_call_counts.get(m.name, 0) + m.calls
            )

    def get_stats(self) -> GatewayStats:
        avg_lat = (
            sum(self.latencies_ms) / len(self.latencies_ms)
            if self.latencies_ms
            else 0.0
        )
        models_used = [
            GatewayModelUsage(name=m, calls=c)
            for m, c in self.models_call_counts.items()
        ]
        return GatewayStats(
            total_requests=self.total_requests,
            total_tokens=self.total_tokens,
            total_cost_usd=round(self.total_cost_usd, 6),
            avg_latency_ms=round(avg_lat, 2),
            cache_hits=self.cache_hits,
            fallbacks_triggered=self.fallbacks_triggered,
            models_used=models_used,
        )


cumulative_gateway_stats = CumulativeGatewayStats()


class BifrostGatewayClient:
    """Thin client wrapping Bifrost's OpenAI-compatible endpoint with automatic fallback."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        openai_client: Optional[AsyncOpenAI] = None,
    ) -> None:
        self.base_url = (base_url or settings.BIFROST_BASE_URL).rstrip("/")
        if openai_client:
            self.client = openai_client
            self.fallback_client = None
        else:
            self.client = AsyncOpenAI(
                base_url=f"{self.base_url}/v1",
                api_key=api_key or settings.GROQ_API_KEY or "bifrost-key",
                timeout=2.0,
                max_retries=0,
            )
            # Automatic fallback client to direct Groq API if Bifrost container is not locally active
            if settings.GROQ_API_KEY:
                self.fallback_client = AsyncOpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=settings.GROQ_API_KEY,
                    timeout=8.0,
                    max_retries=1,
                )
            else:
                self.fallback_client = None

    async def call_structured(
        self,
        task: TaskType | str,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        stats_collector: Optional[GatewayStatsCollector] = None,
        max_retries: int = 2,
        temperature: float = 0.0,
    ) -> T:
        """Calls Bifrost with JSON-mode output, validating against response_model with fallback support."""
        model_name = TASK_MODELS.get(task, task)
        current_messages = list(messages)
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            t0 = time.perf_counter()
            try:
                response = await self.client.chat.completions.create(
                    model=model_name,
                    messages=current_messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
                latency_ms = (time.perf_counter() - t0) * 1000

                # Extract response and token usage
                choice = response.choices[0]
                content = choice.message.content or "{}"
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                actual_model = getattr(response, "model", model_name)

                # Check if fallback was used (model returned differs from requested primary)
                fallback_used = (actual_model != model_name) and (model_name not in actual_model)

                # Parse JSON and validate with Pydantic
                parsed_json = json.loads(content)
                validated_result = response_model.model_validate(parsed_json)

                # Record stats
                if stats_collector:
                    stats_collector.record_call(
                        model=actual_model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=latency_ms,
                        cache_hit=False,
                        fallback_used=fallback_used,
                    )

                return validated_result

            except (json.JSONDecodeError, ValidationError) as err:
                last_error = err
                if attempt < max_retries:
                    # Provide targeted correction feedback to the LLM on retry
                    current_messages.append({
                        "role": "assistant",
                        "content": content if "content" in locals() else "{}",
                    })
                    current_messages.append({
                        "role": "user",
                        "content": (
                            f"Your previous response had a schema/formatting error: {err}. "
                            f"Please return strict, valid JSON matching the required schema."
                        ),
                    })
                else:
                    raise last_error

            except Exception as exc:
                last_error = exc
                # If connection to Bifrost failed and direct fallback is available, trigger fallback
                is_conn_error = (
                    isinstance(exc, (APIConnectionError, httpx.ConnectError))
                    or "Connection error" in str(exc)
                    or "ConnectError" in str(exc)
                )
                if self.fallback_client and is_conn_error:
                    logger.warning(
                        "Bifrost gateway at %s unreachable (%s). Triggering fallback to direct Groq API.",
                        self.base_url,
                        exc,
                    )
                    if stats_collector:
                        stats_collector.record_fallback()
                    try:
                        groq_model = model_name.replace("groq/", "")
                        response = await self.fallback_client.chat.completions.create(
                            model=groq_model,
                            messages=current_messages,
                            response_format={"type": "json_object"},
                            temperature=temperature,
                        )
                        latency_ms = (time.perf_counter() - t0) * 1000
                        choice = response.choices[0]
                        content = choice.message.content or "{}"
                        usage = response.usage
                        prompt_tokens = usage.prompt_tokens if usage else 0
                        completion_tokens = usage.completion_tokens if usage else 0
                        parsed_json = json.loads(content)
                        validated_result = response_model.model_validate(parsed_json)
                        if stats_collector:
                            stats_collector.record_call(
                                model=groq_model,
                                prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens,
                                latency_ms=latency_ms,
                                cache_hit=False,
                                fallback_used=True,
                            )
                        return validated_result
                    except Exception as fallback_exc:
                        logger.error("Direct fallback failed as well: %s", fallback_exc)
                        last_error = fallback_exc

                if attempt >= max_retries:
                    raise last_error

        raise last_error or RuntimeError("Failed to obtain structured response from Bifrost gateway")

