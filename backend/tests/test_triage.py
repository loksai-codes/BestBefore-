from app.pipeline.triage import triage_claims
from app.schemas import Claim, VerifyOptions


def make_claim(id_str: str, c_type: str, volatility: str, is_time: bool) -> Claim:
    return Claim(
        id=id_str,
        text=f"Claim text for {id_str}",
        span_start=0,
        span_end=10,
        entity="Entity",
        attribute="Attr",
        claimed_value="Val",
        claim_type=c_type,  # type: ignore
        volatility=volatility,  # type: ignore
        is_time_sensitive=is_time,
    )


def test_triage_keeps_critical_types():
    claims = [
        make_claim("c1", "pricing", "high", True),
        make_claim("c2", "api_version", "medium", True),
        make_claim("c3", "leadership", "high", True),
        make_claim("c4", "regulation", "medium", True),
    ]

    result = triage_claims(claims)
    assert len(result) == 4
    ids = [c.id for c in result]
    assert "c1" in ids and "c2" in ids and "c3" in ids and "c4" in ids


def test_triage_drops_low_volatility_timeless_facts():
    claims = [
        make_claim("c1", "pricing", "high", True),
        make_claim("c2", "other", "low", False),  # Low-volatility timeless fact -> drop
        make_claim("c3", "other", "medium", True),  # Medium volatility time-sensitive -> keep
    ]

    result = triage_claims(claims)
    ids = [c.id for c in result]
    assert "c1" in ids
    assert "c3" in ids
    assert "c2" not in ids


def test_triage_enforces_max_claims_and_prioritizes():
    claims = [
        make_claim("c-low", "other", "low", True),
        make_claim("c-high-1", "pricing", "high", True),
        make_claim("c-med", "api_version", "medium", True),
        make_claim("c-high-2", "leadership", "high", True),
    ]

    options = VerifyOptions(max_claims=2)
    result = triage_claims(claims, options=options)

    # Max claims is 2, so should pick the 2 high-volatility ones
    assert len(result) == 2
    ids = [c.id for c in result]
    assert "c-high-1" in ids
    assert "c-high-2" in ids

