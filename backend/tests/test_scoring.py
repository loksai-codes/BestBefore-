from datetime import datetime, timedelta, timezone
from app.config import ScoringSettings
from app.pipeline.scoring import (
    calculate_claim_freshness,
    calculate_conflict_penalty,
    calculate_evidence_recency,
    calculate_overall_freshness,
    calculate_source_agreement,
    calculate_source_authority,
    parse_evidence_date,
)
from app.schemas import Claim, ClaimResult, Evidence, ScoreBreakdown


def make_claim(volatility: str = "high", is_time: bool = True) -> Claim:
    return Claim(
        id="c-test",
        text="Sample claim text",
        span_start=0,
        span_end=17,
        entity="OpenAI GPT-4",
        attribute="Pricing",
        claimed_value="$30.00",
        claim_type="pricing",
        volatility=volatility,  # type: ignore
        is_time_sensitive=is_time,
    )


def make_evidence(
    url: str = "https://openai.com/api/pricing/",
    authority: str = "official",
    pub_date: str | None = "2024-10-01",
) -> Evidence:
    return Evidence(
        url=url,
        title="Test Title",
        domain="openai.com",
        snippet="Sample snippet content",
        published_date=pub_date,
        authority=authority,  # type: ignore
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


# 1. Edge Case: No Evidence
def test_scoring_edge_case_no_evidence():
    claim = make_claim(volatility="high", is_time=True)
    score, breakdown, low_conf = calculate_claim_freshness(
        claim=claim,
        verdict="unverifiable",
        evidence=[],
        judge_confidence=0.3,
    )

    assert score <= 40  # Capped at 40
    assert breakdown.source_authority == 0.0
    assert breakdown.evidence_recency == 0.0
    assert breakdown.source_agreement == 0.0
    assert breakdown.conflict_penalty == 1.0
    assert low_conf is True


# 2. Edge Case: One Official Source
def test_scoring_edge_case_one_official_source():
    claim = make_claim(volatility="high", is_time=True)
    ref_date = datetime(2024, 10, 2, tzinfo=timezone.utc)
    ev = [make_evidence(authority="official", pub_date="2024-10-01")]

    score, breakdown, low_conf = calculate_claim_freshness(
        claim=claim,
        verdict="current",
        evidence=ev,
        judge_confidence=1.0,
        supporting_indices=[0],
        reference_date=ref_date,
    )

    assert breakdown.source_authority == 1.0
    assert breakdown.source_agreement == 1.0
    assert breakdown.conflict_penalty == 0.0  # Unanimous official source -> 0 conflict penalty
    assert breakdown.evidence_recency >= 0.95  # 1 day old on 30-day half-life
    assert score >= 90
    assert low_conf is False


# 3. Edge Case: Conflicting Sources
def test_scoring_edge_case_conflicting_sources():
    claim = make_claim(volatility="high", is_time=True)
    ref_date = datetime(2024, 10, 15, tzinfo=timezone.utc)

    # 4 sources: 2 agree, 2 disagree; none are official
    ev = [
        make_evidence(url="https://techcrunch.com/1", authority="reputable", pub_date="2024-10-10"),
        make_evidence(url="https://theverge.com/2", authority="reputable", pub_date="2024-10-09"),
        make_evidence(url="https://reddit.com/3", authority="community", pub_date="2024-10-05"),
        make_evidence(url="https://unverified.xyz/4", authority="unknown", pub_date="2024-10-01"),
    ]

    score, breakdown, _ = calculate_claim_freshness(
        claim=claim,
        verdict="current",
        evidence=ev,
        judge_confidence=0.7,
        supporting_indices=[0, 1],  # Only 2 out of 4 agree
        reference_date=ref_date,
    )

    # 2 out of 4 agree -> 0.50 agreement
    assert breakdown.source_agreement == 0.50
    # Disagreement + no official source -> high conflict penalty
    assert breakdown.conflict_penalty > 0.60
    # Penalty lowers the overall score
    assert score < 70


# 4. Edge Case: Undated Sources
def test_scoring_edge_case_undated_sources():
    claim = make_claim(volatility="medium", is_time=True)
    ev = [
        make_evidence(url="https://openai.com/1", authority="official", pub_date=None),
        make_evidence(url="https://reuters.com/2", authority="reputable", pub_date=""),
    ]

    score, breakdown, _ = calculate_claim_freshness(
        claim=claim,
        verdict="current",
        evidence=ev,
        judge_confidence=0.9,
        supporting_indices=[0, 1],
    )

    # Unknown date default recency is 0.40
    assert breakdown.evidence_recency == 0.40
    assert breakdown.source_authority > 0.80


# 5. Volatility Decay Rate Tests
def test_volatility_half_life_decay():
    claim_high = make_claim(volatility="high")      # 30 days half-life
    claim_medium = make_claim(volatility="medium")  # 180 days half-life
    claim_low = make_claim(volatility="low")        # 730 days half-life

    pub_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Exactly 30 days later
    ref_30d = pub_dt + timedelta(days=30)
    ev = [make_evidence(pub_date="2024-01-01")]

    r_high = calculate_evidence_recency(claim_high, ev, reference_date=ref_30d)
    r_med = calculate_evidence_recency(claim_medium, ev, reference_date=ref_30d)
    r_low = calculate_evidence_recency(claim_low, ev, reference_date=ref_30d)

    # At 30 days:
    # High volatility (half-life=30) should be ~0.50
    assert 0.49 <= r_high <= 0.51
    # Medium volatility (half-life=180) should be much higher (> 0.85)
    assert r_med > 0.85
    # Low volatility (half-life=730) should be near 0.97
    assert r_low > 0.95


# 6. Verdict Caps Enforcement
def test_verdict_caps_enforcement():
    claim = make_claim(volatility="high")
    ev = [make_evidence(authority="official", pub_date="2024-10-01")]
    ref = datetime(2024, 10, 2, tzinfo=timezone.utc)

    # High inputs that would otherwise score ~95
    # Outdated must be capped at 25
    score_outdated, _, _ = calculate_claim_freshness(
        claim, "outdated", ev, judge_confidence=1.0, supporting_indices=[0], reference_date=ref
    )
    assert score_outdated <= 25

    # Partially outdated must be capped at 60
    score_partial, _, _ = calculate_claim_freshness(
        claim, "partially_outdated", ev, judge_confidence=1.0, supporting_indices=[0], reference_date=ref
    )
    assert score_partial <= 60

    # Unverifiable must be capped at 40 and flag low confidence
    score_unverifiable, _, low_conf = calculate_claim_freshness(
        claim, "unverifiable", ev, judge_confidence=1.0, supporting_indices=[0], reference_date=ref
    )
    assert score_unverifiable <= 40
    assert low_conf is True

    # Skipped must be exactly 100
    claim_timeless = make_claim(is_time=False)
    score_skipped, breakdown_skipped, _ = calculate_claim_freshness(
        claim_timeless, "skipped", [], judge_confidence=1.0
    )
    assert score_skipped == 100
    assert breakdown_skipped.source_authority == 1.0


# 7. Overall Freshness Volatility-Weighted Average
def test_calculate_overall_freshness():
    c_high = make_claim(volatility="high")     # weight 3.0
    c_med = make_claim(volatility="medium")    # weight 2.0
    c_low = make_claim(volatility="low")       # weight 1.0
    c_skip = make_claim(is_time=False)         # skipped -> excluded from non-skipped average

    dummy_breakdown = ScoreBreakdown(
        source_authority=1.0,
        evidence_recency=1.0,
        source_agreement=1.0,
        verdict_confidence=1.0,
        conflict_penalty=0.0,
    )

    r_high = ClaimResult(
        claim=c_high, verdict="outdated", freshness_score=20, explanation="", breakdown=dummy_breakdown
    )
    r_med = ClaimResult(
        claim=c_med, verdict="partially_outdated", freshness_score=50, explanation="", breakdown=dummy_breakdown
    )
    r_low = ClaimResult(
        claim=c_low, verdict="current", freshness_score=80, explanation="", breakdown=dummy_breakdown
    )
    r_skip = ClaimResult(
        claim=c_skip, verdict="skipped", freshness_score=100, explanation="timeless/not time-sensitive", breakdown=dummy_breakdown
    )

    # Expected calculation:
    # High: 20 * 3.0 = 60
    # Med:  50 * 2.0 = 100
    # Low:  80 * 1.0 = 80
    # Sum: 240 / (3 + 2 + 1 = 6) = 40.0
    overall = calculate_overall_freshness([r_high, r_med, r_low, r_skip])
    assert overall == 40

    # All claims skipped -> 100
    assert calculate_overall_freshness([r_skip]) == 100
    # Empty list -> 100
    assert calculate_overall_freshness([]) == 100

