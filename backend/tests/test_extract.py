import asyncio

from app.llm.gateway import GatewayStatsCollector
from app.pipeline.extract import (
    ExtractionResponse,
    RawExtractedClaim,
    align_span,
    extract_claims,
)


def test_align_span_exact():
    text = "OpenAI GPT-4 costs $30.00 per million tokens."
    sub = "costs $30.00"
    start = text.index(sub)
    end = start + len(sub)

    res = align_span(text, sub, start, end)
    assert res is not None
    assert res[0] == start
    assert res[1] == end
    assert text[res[0] : res[1]] == sub


def test_align_span_recovers_wrong_offsets():
    text = "Anthropic Claude 3 Opus is priced at $15 per 1M tokens."
    sub = "priced at $15"

    # Pass wrong offsets
    res = align_span(text, sub, 0, 5)
    assert res is not None
    assert text[res[0] : res[1]] == sub


def test_align_span_returns_none_for_missing():
    text = "The sky is blue today."
    res = align_span(text, "costs $30.00", 0, 10)
    assert res is None


class DummyGateway:
    def __init__(self, response: ExtractionResponse):
        self.response = response

    async def call_structured(self, **kwargs):
        return self.response


def test_extract_claims_with_mocked_gateway():
    async def _test():
        answer = (
            "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens. "
            "Python was released in 1991."
        )

        mock_response = ExtractionResponse(
            claims=[
                RawExtractedClaim(
                    text="GPT-4 pricing starts at $30.00 per million prompt tokens",
                    span_start=0,  # Will be aligned by align_span
                    span_end=10,
                    entity="OpenAI GPT-4",
                    attribute="Pricing",
                    claimed_value="$30.00 / 1M tokens",
                    claim_type="pricing",
                    volatility="high",
                    is_time_sensitive=True,
                ),
                RawExtractedClaim(
                    text="Python was released in 1991",
                    span_start=5,  # Will be aligned
                    span_end=20,
                    entity="Python",
                    attribute="Release Year",
                    claimed_value="1991",
                    claim_type="other",
                    volatility="low",
                    is_time_sensitive=False,
                ),
                # Fabricated claim not in text - should be dropped
                RawExtractedClaim(
                    text="This sentence does not exist in the answer",
                    span_start=0,
                    span_end=5,
                    entity="Phantom",
                    attribute="Fake",
                    claimed_value="None",
                    claim_type="other",
                    volatility="low",
                    is_time_sensitive=False,
                ),
            ]
        )

        dummy_client = DummyGateway(mock_response)
        collector = GatewayStatsCollector()

        claims = await extract_claims(answer, gateway=dummy_client, stats_collector=collector)  # type: ignore

        # 2 valid claims kept, 1 hallucinated claim dropped
        assert len(claims) == 2

        # Verify all extracted spans strictly match original answer text
        for c in claims:
            assert answer[c.span_start : c.span_end] == c.text

        # First claim is time-sensitive pricing
        assert claims[0].claim_type == "pricing"
        assert claims[0].is_time_sensitive is True
        assert claims[0].volatility == "high"

        # Second claim is historical fact (is_time_sensitive=False)
        assert claims[1].is_time_sensitive is False

    asyncio.run(_test())
