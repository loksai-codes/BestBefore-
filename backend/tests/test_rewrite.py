import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.llm.gateway import GatewayStatsCollector, cumulative_gateway_stats
from app.main import get_gateway_stats, rate_limiter
from app.pipeline.rewrite import (
    RewriteLLMOutput,
    build_citation_map,
    deterministic_span_replacement,
    generate_rewritten_answer,
    validate_rewritten_answer,
)
from app.schemas import Claim, ClaimResult, Evidence, ScoreBreakdown


def make_claim_result(
    claim_id: str,
    text: str,
    claimed_val: str,
    verdict: str,
    current_val: str | None,
    url: str = "https://example.com/source",
) -> ClaimResult:
    claim = Claim(
        id=claim_id,
        text=text,
        span_start=0,
        span_end=len(text),
        entity="TestEntity",
        attribute="TestAttr",
        claimed_value=claimed_val,
        claim_type="pricing",
        volatility="high",
        is_time_sensitive=True,
    )
    breakdown = ScoreBreakdown(
        source_authority=1.0,
        evidence_recency=1.0,
        source_agreement=1.0,
        verdict_confidence=0.95,
        conflict_penalty=0.0,
    )
    evidence = [
        Evidence(
            url=url,
            title="Source Title",
            domain="example.com",
            snippet="Source snippet",
            published_date="2024-01-01",
            authority="official",
            retrieved_at="2024-01-01T00:00:00Z",
        )
    ]
    return ClaimResult(
        claim=claim,
        verdict=verdict,  # type: ignore
        freshness_score=25 if verdict == "outdated" else 95,
        current_value=current_val,
        explanation="Test explanation",
        evidence=evidence,
        breakdown=breakdown,
        history=[],
    )


def test_build_citation_map():
    res1 = make_claim_result("c1", "text 1", "old 1", "outdated", "new 1", "https://url1.com")
    res2 = make_claim_result("c2", "text 2", "old 2", "current", "old 2", "https://url2.com")
    res3 = make_claim_result("c3", "text 3", "old 3", "outdated", "new 3", "https://url1.com")

    url_map, urls = build_citation_map([res1, res2, res3])
    assert len(urls) == 2
    assert url_map["https://url1.com"] == 1
    assert url_map["https://url2.com"] == 2


def test_deterministic_span_replacement():
    original = "GPT-4 is priced at $30 per million tokens. Founded in 2015."
    res = make_claim_result(
        "c1",
        "GPT-4 is priced at $30 per million tokens",
        "$30",
        "outdated",
        "$2.50",
        "https://openai.com/pricing",
    )
    url_map = {"https://openai.com/pricing": 1}

    rewritten = deterministic_span_replacement(original, [res], url_map)
    assert "$2.50 [1]" in rewritten
    assert "$30" not in rewritten
    assert "Founded in 2015" in rewritten


def test_validate_rewritten_answer():
    original = "GPT-4 pricing is $30. Founded in 2015 by Sam Altman."
    res_outdated = make_claim_result("c1", "GPT-4 pricing is $30", "$30", "outdated", "$2.50")
    res_current = make_claim_result("c2", "Founded in 2015", "2015", "current", "2015")

    # Valid: preserves unchanged claim "2015"
    valid_candidate = "GPT-4 pricing is $2.50 [1]. Founded in 2015 by Sam Altman."
    assert validate_rewritten_answer(original, valid_candidate, [res_outdated, res_current]) is True

    # Invalid: deleted unchanged claim fact "2015"
    invalid_candidate = "GPT-4 pricing is now $2.50."
    assert validate_rewritten_answer(original, invalid_candidate, [res_outdated, res_current]) is False


def test_generate_rewritten_answer_with_mocked_gateway():
    async def _test():
        original = "The CEO of Starbucks is Laxman Narasimhan."
        res = make_claim_result(
            "c1",
            "The CEO of Starbucks is Laxman Narasimhan",
            "Laxman Narasimhan",
            "outdated",
            "Brian Niccol",
            "https://starbucks.com/press",
        )

        mock_gateway = MagicMock()
        mock_gateway.call_structured = AsyncMock(
            return_value=RewriteLLMOutput(
                rewritten_answer="The CEO of Starbucks is Brian Niccol [1].",
                changes_made=["Replaced Laxman Narasimhan with Brian Niccol"],
            )
        )

        rewritten = await generate_rewritten_answer(
            original, [res], gateway=mock_gateway
        )
        assert rewritten is not None
        assert "Brian Niccol [1]" in rewritten
        assert "Sources:" in rewritten
        assert "https://starbucks.com/press" in rewritten

    asyncio.run(_test())


def test_cumulative_gateway_stats_endpoint():
    async def _test():
        collector = GatewayStatsCollector()
        collector.record_call(
            model="llama-3.1-8b-instant",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=120.0,
            cache_hit=True,
            fallback_used=False,
        )
        cumulative_gateway_stats.record_request_stats(collector.get_stats())

        stats = await get_gateway_stats()
        assert stats.total_requests >= 1
        assert stats.total_tokens >= 150
        assert stats.cache_hits >= 1

    asyncio.run(_test())


def test_rate_limiter():
    limiter = rate_limiter
    test_ip = "192.168.1.99"
    # First request allowed
    assert limiter.is_allowed(test_ip) is True

