import asyncio
import os
import uuid
from datetime import datetime, timezone
import pytest

from app.config import settings
from app.graph.client import GraphStore
from app.schemas import Claim, ClaimResult, Evidence, ScoreBreakdown

# Skip tests if FalkorDB credentials are missing
pytestmark = pytest.mark.skipif(
    not settings.FALKORDB_HOST,
    reason="FALKORDB_HOST not configured. Skipping FalkorDB Cloud tests.",
)


@pytest.fixture
def graph_test_store():
    """Provides a GraphStore pointed at the isolated test graph name."""
    store = GraphStore(
        host=settings.FALKORDB_HOST,
        port=settings.FALKORDB_PORT,
        username=settings.FALKORDB_USERNAME,
        password=settings.FALKORDB_PASSWORD,
        ssl=settings.FALKORDB_SSL,
        graph_name=settings.FALKORDB_GRAPH_TEST or "bestbefore_test",
        socket_timeout=5,
        connect_timeout=5,
    )
    return store


def test_graph_connection_and_stats(graph_test_store):
    async def _test():
        connected = await graph_test_store.connect()
        assert connected is True
        assert graph_test_store.is_available is True

        health = await graph_test_store.health_check()
        assert health is True

        stats = await graph_test_store.get_stats()
        assert stats["available"] is True
        assert "nodes" in stats
        assert stats["graph"] == (settings.FALKORDB_GRAPH_TEST or "bestbefore_test")

    asyncio.run(_test())


def test_bitemporal_upsert_and_supersedes(graph_test_store):
    async def _test():
        await graph_test_store.connect()

        unique_entity = f"Entity-{uuid.uuid4()}"
        attr = "pricing"

        claim = Claim(
            id=f"c-{uuid.uuid4()}",
            text=f"{unique_entity} initial pricing $50",
            span_start=0,
            span_end=10,
            entity=unique_entity,
            attribute=attr,
            claimed_value="$50.00",
            claim_type="pricing",
            volatility="high",
            is_time_sensitive=True,
        )

        dummy_breakdown = ScoreBreakdown(
            source_authority=1.0,
            evidence_recency=1.0,
            source_agreement=1.0,
            verdict_confidence=0.95,
            conflict_penalty=0.0,
        )

        # 1. Initial verification: $50 is current
        res1 = ClaimResult(
            claim=claim,
            verdict="current",
            freshness_score=95,
            current_value="$50.00",
            explanation="Initial pricing confirmed.",
            evidence=[
                Evidence(
                    url="https://test.com/pricing",
                    title="Pricing",
                    domain="test.com",
                    snippet="Price is $50",
                    published_date="2024-01-01",
                    authority="official",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                )
            ],
            breakdown=dummy_breakdown,
        )
        await graph_test_store.upsert_verification(claim, res1)

        # Verify initial fact created
        hist1 = await graph_test_store.get_history(unique_entity, attr)
        assert len(hist1) == 1
        assert hist1[0].value == "$50.00"

        # 2. Second verification: pricing updated to $20 (outdated)
        res2 = ClaimResult(
            claim=claim,
            verdict="outdated",
            freshness_score=25,
            current_value="$20.00",
            explanation="Price reduced to $20.",
            evidence=[
                Evidence(
                    url="https://test.com/new-pricing",
                    title="New Pricing",
                    domain="test.com",
                    snippet="Price dropped to $20",
                    published_date="2024-06-01",
                    authority="official",
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                )
            ],
            breakdown=dummy_breakdown,
        )
        await graph_test_store.upsert_verification(claim, res2)

        # 3. Check history: must now have 2 facts, old superseded by new
        hist2 = await graph_test_store.get_history(unique_entity, attr)
        assert len(hist2) == 2
        values = [h.value for h in hist2]
        assert "$50.00" in values
        assert "$20.00" in values

        # 4. Bi-temporal as-of check
        # As of early 2024: $50
        as_of_old = await graph_test_store.as_of(unique_entity, attr, "2024-02-01")
        assert as_of_old is not None
        assert as_of_old["value"] == "$50.00"

        # As of late 2024: $20
        as_of_new = await graph_test_store.as_of(unique_entity, attr, "2024-07-01")
        assert as_of_new is not None
        assert as_of_new["value"] == "$20.00"

        # 5. Recent verification cache hit check
        recent = await graph_test_store.get_recent_verification(unique_entity, attr, "high")
        assert recent is not None
        assert recent.current_value == "$20.00"
        assert recent.verdict == "outdated"

    asyncio.run(_test())


def test_graceful_degradation_when_unreachable():
    async def _test():
        # Store pointing to non-existent host
        bad_store = GraphStore(
            host="127.0.0.1",
            port=59999,
            username="nobody",
            password="wrong",
            socket_timeout=1,
            connect_timeout=1,
        )

        connected = await bad_store.connect()
        assert connected is False
        assert bad_store.is_available is False

        # Calls must not raise exceptions; should return empty / safe defaults
        health = await bad_store.health_check()
        assert health is False

        stats = await bad_store.get_stats()
        assert stats["available"] is False

        hist = await bad_store.get_history("SomeEntity", "SomeAttr")
        assert hist == []

        as_of = await bad_store.as_of("SomeEntity", "SomeAttr", "2024-01-01")
        assert as_of is None

        recent = await bad_store.get_recent_verification("SomeEntity", "SomeAttr")
        assert recent is None

    asyncio.run(_test())

