import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.pipeline.judge import RawJudgeOutput
from app.pipeline.verify import (
    VerificationEngine,
    classify_authority,
    extract_domain,
    infer_entity_domain,
    query_builder,
)
from app.schemas import Claim, ClaimResult
from tests.fixtures.tavily_fixtures import (
    FIXTURE_LEADERSHIP_EXTRACT,
    FIXTURE_LEADERSHIP_SEARCH,
    FIXTURE_PRICING_EXTRACT,
    FIXTURE_PRICING_SEARCH,
    FIXTURE_REGULATION_EXTRACT,
    FIXTURE_REGULATION_SEARCH,
)


def make_test_claim(
    id_str: str,
    entity: str,
    attr: str,
    claimed_val: str,
    c_type: str,
    text: str,
    is_time: bool = True,
) -> Claim:
    return Claim(
        id=id_str,
        text=text,
        span_start=0,
        span_end=len(text),
        entity=entity,
        attribute=attr,
        claimed_value=claimed_val,
        claim_type=c_type,  # type: ignore
        volatility="high",
        is_time_sensitive=is_time,
    )


def test_query_builder_generates_targeted_queries():
    c_price = make_test_claim(
        "1", "OpenAI GPT-4", "API Pricing", "$30/1M tokens", "pricing", "GPT-4 costs $30"
    )
    queries = query_builder(c_price)
    assert len(queries) >= 1
    assert "OpenAI GPT-4" in queries[0]
    assert "pricing" in queries[0].lower()

    c_lead = make_test_claim(
        "2", "Starbucks", "CEO", "Laxman Narasimhan", "leadership", "CEO is Laxman"
    )
    q_lead = query_builder(c_lead)
    assert any("Starbucks" in q and "CEO" in q for q in q_lead)

    c_reg = make_test_claim(
        "3", "FTC", "Non-Compete Rule", "Effective Sept 4", "regulation", "FTC ban in effect"
    )
    q_reg = query_builder(c_reg)
    assert any("FTC" in q for q in q_reg)


def test_authority_classification():
    # Official matching known domain
    assert classify_authority("https://openai.com/api/pricing/", "OpenAI") == "official"
    assert classify_authority("https://docs.anthropic.com/models", "Anthropic") == "official"
    # Official government domains
    assert classify_authority("https://www.ftc.gov/press-release", "FTC") == "official"
    assert classify_authority("https://digital-strategy.ec.europa.eu/ai-act", "EU") == "official"

    # Reputable news / press
    assert classify_authority("https://www.reuters.com/business/article", "Starbucks") == "reputable"
    assert classify_authority("https://techcrunch.com/article", "OpenAI") == "reputable"

    # Community forums / blogs
    assert classify_authority("https://www.reddit.com/r/technology", "Twitter") == "community"

    # Unknown general domain
    assert classify_authority("https://random-unverified-blog.xyz/post", "Microsoft") == "unknown"


def test_verify_pricing_claim_with_fixtures():
    async def _test():
        claim = make_test_claim(
            "claim-p",
            "OpenAI GPT-4",
            "Prompt Token Pricing",
            "$30.00 / 1M tokens",
            "pricing",
            "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens.",
        )

        mock_tavily = MagicMock()
        mock_tavily.search = MagicMock(return_value=FIXTURE_PRICING_SEARCH)
        mock_tavily.extract = MagicMock(return_value=FIXTURE_PRICING_EXTRACT)

        mock_gateway = MagicMock()
        mock_gateway.call_structured = AsyncMock(
            return_value=RawJudgeOutput(
                verdict="outdated",
                current_value="GPT-4o at $2.50 / 1M tokens",
                explanation="OpenAI introduced GPT-4o at $2.50/1M tokens, reducing original $30/1M pricing.",
                confidence=0.96,
                supporting_evidence_indices=[0, 1],
            )
        )

        engine = VerificationEngine(tavily_client=mock_tavily, gateway=mock_gateway)
        result: ClaimResult = await engine.verify_single_claim(claim)

        assert result.verdict == "outdated"
        assert result.current_value == "GPT-4o at $2.50 / 1M tokens"
        assert result.freshness_score < 30
        assert len(result.evidence) >= 1
        assert result.evidence[0].authority == "official"

    asyncio.run(_test())


def test_verify_leadership_claim_with_fixtures():
    async def _test():
        claim = make_test_claim(
            "claim-lead",
            "Starbucks",
            "CEO",
            "Laxman Narasimhan",
            "leadership",
            "Laxman Narasimhan leads Starbucks as CEO.",
        )

        mock_tavily = MagicMock()
        mock_tavily.search = MagicMock(return_value=FIXTURE_LEADERSHIP_SEARCH)
        mock_tavily.extract = MagicMock(return_value=FIXTURE_LEADERSHIP_EXTRACT)

        mock_gateway = MagicMock()
        mock_gateway.call_structured = AsyncMock(
            return_value=RawJudgeOutput(
                verdict="outdated",
                current_value="Brian Niccol",
                explanation="Brian Niccol was appointed Chairman and CEO of Starbucks on September 9, 2024.",
                confidence=0.98,
                supporting_evidence_indices=[0],
            )
        )

        engine = VerificationEngine(tavily_client=mock_tavily, gateway=mock_gateway)
        result = await engine.verify_single_claim(claim)

        assert result.verdict == "outdated"
        assert "Brian Niccol" in (result.current_value or "")
        assert result.freshness_score < 30
        assert len(result.evidence) >= 1

    asyncio.run(_test())


def test_verify_regulation_claim_with_fixtures():
    async def _test():
        claim = make_test_claim(
            "claim-reg",
            "FTC",
            "Non-Compete Ban",
            "Took effect Sept 4, 2024",
            "regulation",
            "The FTC nationwide ban on non-compete agreements took effect on September 4, 2024.",
        )

        mock_tavily = MagicMock()
        mock_tavily.search = MagicMock(return_value=FIXTURE_REGULATION_SEARCH)
        mock_tavily.extract = MagicMock(return_value=FIXTURE_REGULATION_EXTRACT)

        mock_gateway = MagicMock()
        mock_gateway.call_structured = AsyncMock(
            return_value=RawJudgeOutput(
                verdict="outdated",
                current_value="Enjoined & Struck Down Nationwide",
                explanation="A Texas federal court struck down and enjoined the rule nationwide in August 2024.",
                confidence=0.97,
                supporting_evidence_indices=[0, 1],
            )
        )

        engine = VerificationEngine(tavily_client=mock_tavily, gateway=mock_gateway)
        result = await engine.verify_single_claim(claim)

        assert result.verdict == "outdated"
        assert result.current_value == "Enjoined & Struck Down Nationwide"
        assert result.evidence[0].authority == "official"

    asyncio.run(_test())


def test_per_claim_error_isolation():
    async def _test():
        # Claim 1 will raise an error during search
        failing_claim = make_test_claim("c-fail", "BrokenEntity", "Attr", "Val", "other", "Failing claim")
        # Claim 2 succeeds
        normal_claim = make_test_claim("c-ok", "NormalEntity", "Attr", "Val", "other", "Normal claim", is_time=False)

        mock_tavily = MagicMock()
        mock_tavily.search.side_effect = RuntimeError("Tavily rate limit exceeded")

        engine = VerificationEngine(tavily_client=mock_tavily)
        results = await engine.verify_claims([failing_claim, normal_claim])

        assert len(results) == 2
        # Failing claim fell back safely without crashing request
        assert results[0].verdict == "unverifiable"
        # Normal timeless claim succeeded as skipped
        assert results[1].verdict == "skipped"

    asyncio.run(_test())
