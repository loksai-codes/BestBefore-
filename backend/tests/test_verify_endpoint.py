import asyncio
from unittest.mock import AsyncMock, patch
from app.main import verify_answer
from app.schemas import Claim, VerifyRequest


def test_verify_endpoint_flow():
    async def _test():
        mock_claims = [
            Claim(
                id="test-c1",
                text="GPT-4 is priced at $30",
                span_start=0,
                span_end=22,
                entity="OpenAI GPT-4",
                attribute="Pricing",
                claimed_value="$30",
                claim_type="pricing",
                volatility="high",
                is_time_sensitive=True,
            ),
            Claim(
                id="test-c2",
                text="Founded in 2015",
                span_start=24,
                span_end=39,
                entity="OpenAI",
                attribute="Founded",
                claimed_value="2015",
                claim_type="other",
                volatility="low",
                is_time_sensitive=False,
            ),
        ]

        with patch("app.main.extract_claims", new=AsyncMock(return_value=mock_claims)):
            req = VerifyRequest(
                answer="GPT-4 is priced at $30. Founded in 2015."
            )
            response = await verify_answer(req)

            assert response.answer == req.answer
            assert len(response.results) >= 1

            # Check contract conformity
            for r in response.results:
                assert r.claim is not None
                assert r.verdict in ["unverifiable", "skipped"]
                assert 0 <= r.freshness_score <= 100
                assert r.breakdown is not None

            assert 0 <= response.overall_freshness <= 100
            assert response.duration_ms >= 0

    asyncio.run(_test())
