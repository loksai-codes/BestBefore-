import asyncio
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel

from app.llm.gateway import (
    BifrostGatewayClient,
    GatewayStatsCollector,
    estimate_cost,
)


class SampleModel(BaseModel):
    message: str
    count: int


def test_gateway_stats_collector():
    collector = GatewayStatsCollector()

    collector.record_call(
        model="groq/llama-3.1-8b-instant",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=120.0,
        cache_hit=False,
        fallback_used=False,
    )

    collector.record_call(
        model="groq/llama-3.3-70b-versatile",
        prompt_tokens=2000,
        completion_tokens=1000,
        latency_ms=300.0,
        cache_hit=True,
        fallback_used=True,
    )

    stats = collector.get_stats()
    assert stats.total_requests == 2
    assert stats.total_tokens == 4500
    assert stats.cache_hits == 1
    assert stats.fallbacks_triggered == 1
    assert stats.avg_latency_ms == 210.0
    assert stats.total_cost_usd > 0
    assert len(stats.models_used) == 2


def test_call_structured_success():
    async def _test():
        mock_openai = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"message": "Hello Bifrost", "count": 42}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.model = "groq/llama-3.1-8b-instant"
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)

        client = BifrostGatewayClient(openai_client=mock_openai)
        collector = GatewayStatsCollector()

        result = await client.call_structured(
            task="extract",
            messages=[{"role": "user", "content": "hi"}],
            response_model=SampleModel,
            stats_collector=collector,
        )

        assert result.message == "Hello Bifrost"
        assert result.count == 42
        assert collector.total_requests == 1
        assert collector.total_tokens == 150

    asyncio.run(_test())


def test_call_structured_retry_on_invalid_json():
    async def _test():
        mock_openai = MagicMock()

        # First attempt: invalid JSON
        bad_choice = MagicMock()
        bad_choice.message.content = 'Not valid json'
        bad_response = MagicMock()
        bad_response.choices = [bad_choice]
        bad_response.model = "groq/llama-3.1-8b-instant"
        bad_response.usage.prompt_tokens = 50
        bad_response.usage.completion_tokens = 20

        # Second attempt: valid JSON
        good_choice = MagicMock()
        good_choice.message.content = '{"message": "Recovered", "count": 99}'
        good_response = MagicMock()
        good_response.choices = [good_choice]
        good_response.model = "groq/llama-3.1-8b-instant"
        good_response.usage.prompt_tokens = 80
        good_response.usage.completion_tokens = 40

        mock_openai.chat.completions.create = AsyncMock(
            side_effect=[bad_response, good_response]
        )

        client = BifrostGatewayClient(openai_client=mock_openai)
        collector = GatewayStatsCollector()

        result = await client.call_structured(
            task="extract",
            messages=[{"role": "user", "content": "test"}],
            response_model=SampleModel,
            stats_collector=collector,
            max_retries=2,
        )

        assert result.message == "Recovered"
        assert result.count == 99
        assert mock_openai.chat.completions.create.call_count == 2

    asyncio.run(_test())
