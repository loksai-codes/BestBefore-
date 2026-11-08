"""Demonstration script to verify a sample stale answer and print a comprehensive readable report.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.pipeline.judge import RawJudgeOutput
from app.pipeline.scoring import calculate_overall_freshness
from app.pipeline.verify import VerificationEngine
from app.schemas import Claim, ClaimResult, GatewayStats, VerifyOptions, VerifyRequest, VerifyResponse
from tests.fixtures.tavily_fixtures import (
    FIXTURE_PRICING_EXTRACT,
    FIXTURE_PRICING_SEARCH,
)

SAMPLE_ANSWER = (
    "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens and $60.00 per million completion tokens. "
    "In comparison, Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens."
)


async def run_verification():
    print("=" * 80)
    print("  BESTBEFORE - VERIFICATION PIPELINE REPORT")
    print("  \"A best-before date for every AI answer.\"")
    print("=" * 80)
    print(f"\n[INPUT ANSWER]\n\"{SAMPLE_ANSWER}\"\n")

    # Mocked Tavily and LLM Judge for reproducible, deterministic demonstration
    mock_tavily = MagicMock()
    mock_tavily.search = MagicMock(return_value=FIXTURE_PRICING_SEARCH)
    mock_tavily.extract = MagicMock(return_value=FIXTURE_PRICING_EXTRACT)

    mock_gateway = MagicMock()

    # Define judge behavior for the claims
    async def fake_call_structured(task, messages, response_model, stats_collector=None, **kwargs):
        content_str = str(messages)
        if "Claude 3 Opus" in content_str:
            return RawJudgeOutput(
                verdict="current",
                current_value="$15.00 / 1M input, $75.00 / 1M output",
                explanation="Anthropic's official pricing page confirms Claude 3 Opus remains at $15/1M input and $75/1M output.",
                confidence=0.98,
                supporting_evidence_indices=[0],
            )
        else:
            return RawJudgeOutput(
                verdict="outdated",
                current_value="GPT-4o at $2.50 / 1M tokens",
                explanation="OpenAI deprecated original GPT-4 pricing in favor of GPT-4o priced at $2.50 per 1M prompt tokens.",
                confidence=0.96,
                supporting_evidence_indices=[0, 1],
            )

    mock_gateway.call_structured = AsyncMock(side_effect=fake_call_structured)

    # 1. Extracted & Triaged claims
    claims = [
        Claim(
            id="claim-gpt4-pricing",
            text="OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens",
            span_start=0,
            span_end=65,
            entity="OpenAI GPT-4",
            attribute="Prompt Token Pricing",
            claimed_value="$30.00 per million prompt tokens",
            claim_type="pricing",
            volatility="high",
            is_time_sensitive=True,
        ),
        Claim(
            id="claim-claude-pricing",
            text="Anthropic Claude 3 Opus costs $15.00 per 1M input tokens and $75.00 per 1M output tokens",
            span_start=107,
            span_end=195,
            entity="Anthropic Claude 3 Opus",
            attribute="Pricing",
            claimed_value="$15.00 input / $75.00 output",
            claim_type="pricing",
            volatility="high",
            is_time_sensitive=True,
        ),
    ]

    print(f"Extracted & Triaged Claims: {len(claims)} time-sensitive claims identified.")

    engine = VerificationEngine(tavily_client=mock_tavily, gateway=mock_gateway)
    results = await engine.verify_claims(claims)
    overall_freshness = calculate_overall_freshness(results)

    print("\n" + "-" * 80)
    print(f"  OVERALL FRESHNESS SCORE: {overall_freshness}/100")
    print("-" * 80)

    for i, res in enumerate(results, start=1):
        c = res.claim
        print(f"\nClaim #{i}:")
        print(f"  Text:          \"{c.text}\" (offset: [{c.span_start}:{c.span_end}])")
        print(f"  Entity/Attr:   {c.entity} -> {c.attribute} [{c.claim_type.upper()}] (volatility: {c.volatility})")
        print(f"  Claimed Value: {c.claimed_value}")
        print(f"  Verified Value:{res.current_value or 'N/A'}")
        
        status_symbol = "[OK] CURRENT" if res.verdict == "current" else "[X] OUTDATED"
        print(f"  Verdict:       {status_symbol} (Score: {res.freshness_score}/100)")
        print(f"  Explanation:   {res.explanation}")

        b = res.breakdown
        print(f"  Score Breakdown:")
        print(f"    - Source Authority:   {b.source_authority:.2f} (official sources weighted highest)")
        print(f"    - Evidence Recency:   {b.evidence_recency:.2f} (half-life decay relative to volatility)")
        print(f"    - Source Agreement:   {b.source_agreement:.2f}")
        print(f"    - Verdict Confidence: {b.verdict_confidence:.2f}")
        print(f"    - Conflict Penalty:   {b.conflict_penalty:.2f}")

        print(f"  Evidence Sources ({len(res.evidence)} found):")
        for ev in res.evidence:
            print(f"    * [{ev.authority.upper()}] {ev.domain} (pub: {ev.published_date or 'N/A'})")
            print(f"      URL: {ev.url}")
            print(f"      Snippet: {ev.snippet[:120].strip()}...")

    # Generate corrected answer
    corrected = SAMPLE_ANSWER
    for res in results:
        if res.verdict in ["outdated", "partially_outdated"] and res.current_value:
            corrected = corrected.replace(res.claim.claimed_value, res.current_value)

    print("\n" + "=" * 80)
    print("  CORRECTED ANSWER (REWRITE):")
    print("=" * 80)
    print(f"Original:  {SAMPLE_ANSWER}")
    print(f"Corrected: {corrected}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_verification())

