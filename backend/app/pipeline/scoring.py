import math
import re
from datetime import datetime, timezone
from typing import List, Optional

from app.config import ScoringSettings, scoring_settings
from app.schemas import Claim, ClaimResult, Evidence, ScoreBreakdown, Verdict


def parse_evidence_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parses published date string into timezone-aware datetime."""
    if not date_str:
        return None

    cleaned = date_str.strip()
    if not cleaned:
        return None

    # Try ISO formats
    try:
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # Regex search for YYYY-MM-DD
    match = re.search(r"\b(20[1-3][0-9])-([0-1][0-9])-([0-3][0-9])\b", cleaned)
    if match:
        try:
            return datetime(
                year=int(match.group(1)),
                month=int(match.group(2)),
                day=int(match.group(3)),
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass

    # Regex search for YYYY-MM
    match_ym = re.search(r"\b(20[1-3][0-9])-([0-1][0-9])\b", cleaned)
    if match_ym:
        try:
            return datetime(
                year=int(match_ym.group(1)),
                month=int(match_ym.group(2)),
                day=1,
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass

    # Regex search for standalone year YYYY
    match_y = re.search(r"\b(20[1-3][0-9])\b", cleaned)
    if match_y:
        return datetime(
            year=int(match_y.group(1)),
            month=1,
            day=1,
            tzinfo=timezone.utc,
        )

    return None


def calculate_source_authority(
    evidence: List[Evidence],
    supporting_indices: Optional[List[int]] = None,
    config: ScoringSettings = scoring_settings,
) -> float:
    """Computes weighted mean of evidence authority, weighted toward supporting evidence."""
    if not evidence:
        return 0.0

    sup_set = set(supporting_indices or [])
    total_weighted_score = 0.0
    total_weights = 0.0

    for i, ev in enumerate(evidence):
        base_auth = config.authority_weights.get(
            ev.authority, config.authority_weights["unknown"]
        )
        weight = config.supporting_evidence_weight if i in sup_set else 1.0
        total_weighted_score += weight * base_auth
        total_weights += weight

    if total_weights <= 0.0:
        return 0.0

    return min(1.0, max(0.0, total_weighted_score / total_weights))


def calculate_evidence_recency(
    claim: Claim,
    evidence: List[Evidence],
    supporting_indices: Optional[List[int]] = None,
    reference_date: Optional[datetime] = None,
    config: ScoringSettings = scoring_settings,
) -> float:
    """Computes evidence recency based on half-life decay according to claim volatility."""
    if not evidence:
        return 0.0

    ref_dt = reference_date or datetime.now(timezone.utc)
    half_life_days = config.volatility_half_lives.get(
        claim.volatility, config.volatility_half_lives["medium"]
    )

    sup_set = set(supporting_indices or [])
    total_weighted_recency = 0.0
    total_weights = 0.0

    for i, ev in enumerate(evidence):
        weight = config.supporting_evidence_weight if i in sup_set else 1.0
        pub_dt = parse_evidence_date(ev.published_date)

        if pub_dt is None:
            r_i = config.unknown_date_recency
        else:
            age_days = max(0.0, (ref_dt - pub_dt).total_seconds() / 86400.0)
            # Exponential half-life decay: 0.5^(age_days / half_life_days)
            r_i = math.pow(0.5, age_days / float(half_life_days))

        total_weighted_recency += weight * r_i
        total_weights += weight

    if total_weights <= 0.0:
        return 0.0

    return min(1.0, max(0.0, total_weighted_recency / total_weights))


def calculate_source_agreement(
    evidence: List[Evidence],
    supporting_indices: Optional[List[int]] = None,
) -> float:
    """Computes the fraction of evidence agreeing with the judged current value."""
    if not evidence:
        return 0.0

    if not supporting_indices:
        return 0.0

    # Count valid indices within bounds
    agreeing = sum(1 for i in set(supporting_indices) if 0 <= i < len(evidence))
    return min(1.0, max(0.0, agreeing / len(evidence)))


def calculate_conflict_penalty(
    evidence: List[Evidence],
    source_agreement: float,
    config: ScoringSettings = scoring_settings,
) -> float:
    """Computes penalty in [0..1] when sources disagree or no official source exists."""
    if not evidence:
        return 1.0

    disagreement = 1.0 - source_agreement
    has_official = any(ev.authority == "official" for ev in evidence)
    no_official_penalty = config.no_official_source_penalty if not has_official else 0.0

    penalty = (disagreement * (1.0 - no_official_penalty)) + no_official_penalty
    return min(1.0, max(0.0, penalty))


def calculate_claim_freshness(
    claim: Claim,
    verdict: Verdict,
    evidence: List[Evidence],
    judge_confidence: float,
    supporting_indices: Optional[List[int]] = None,
    reference_date: Optional[datetime] = None,
    config: ScoringSettings = scoring_settings,
) -> tuple[int, ScoreBreakdown, bool]:
    """Calculates deterministic freshness score and ScoreBreakdown for a single claim.

    Returns:
        (freshness_score [0..100], ScoreBreakdown, low_confidence_flag)
    """
    # Special verdict: skipped (timeless / not time-sensitive)
    if verdict == "skipped" or not claim.is_time_sensitive:
        breakdown = ScoreBreakdown(
            source_authority=1.0,
            evidence_recency=1.0,
            source_agreement=1.0,
            verdict_confidence=1.0,
            conflict_penalty=0.0,
        )
        return config.verdict_caps["skipped"], breakdown, False

    # Component 1: Source Authority
    authority = calculate_source_authority(
        evidence=evidence,
        supporting_indices=supporting_indices,
        config=config,
    )

    # Component 2: Evidence Recency
    recency = calculate_evidence_recency(
        claim=claim,
        evidence=evidence,
        supporting_indices=supporting_indices,
        reference_date=reference_date,
        config=config,
    )

    # Component 3: Source Agreement
    agreement = calculate_source_agreement(
        evidence=evidence,
        supporting_indices=supporting_indices,
    )

    # Component 4: Verdict Confidence
    confidence = min(1.0, max(0.0, float(judge_confidence)))

    # Component 5: Conflict Penalty
    conflict_penalty = calculate_conflict_penalty(
        evidence=evidence,
        source_agreement=agreement,
        config=config,
    )

    # Base weighted sum: 0.30*auth + 0.25*rec + 0.25*agr + 0.20*conf
    weights = config.base_weights
    base = (
        weights["authority"] * authority
        + weights["recency"] * recency
        + weights["agreement"] * agreement
        + weights["confidence"] * confidence
    )

    # Apply penalty: base * (1 - penalty_factor * conflict_penalty)
    penalized_base = base * (1.0 - (config.penalty_factor * conflict_penalty))
    raw_score = int(round(100.0 * penalized_base))

    # Apply verdict-based score mapping and caps
    low_confidence_flag = False

    if verdict == "current":
        score = min(config.verdict_caps["current"], max(0, raw_score))
    elif verdict == "partially_outdated":
        score = min(config.verdict_caps["partially_outdated"], max(0, raw_score))
    elif verdict == "outdated":
        score = min(config.verdict_caps["outdated"], max(0, raw_score))
    elif verdict == "unverifiable":
        score = min(config.verdict_caps["unverifiable"], max(0, raw_score))
        low_confidence_flag = True
    else:
        score = min(100, max(0, raw_score))

    breakdown = ScoreBreakdown(
        source_authority=round(authority, 2),
        evidence_recency=round(recency, 2),
        source_agreement=round(agreement, 2),
        verdict_confidence=round(confidence, 2),
        conflict_penalty=round(conflict_penalty, 2),
    )

    return score, breakdown, low_confidence_flag


def calculate_overall_freshness(
    results: List[ClaimResult],
    config: ScoringSettings = scoring_settings,
) -> int:
    """Computes overall freshness as a volatility-weighted average across non-skipped claims.

    If all claims are skipped or empty, returns 100.
    """
    non_skipped = [r for r in results if r.verdict != "skipped"]
    if not non_skipped:
        return 100

    weighted_score_sum = 0.0
    total_weights = 0.0

    for res in non_skipped:
        weight = config.volatility_weights.get(
            res.claim.volatility, config.volatility_weights["medium"]
        )
        weighted_score_sum += weight * res.freshness_score
        total_weights += weight

    if total_weights <= 0.0:
        return 100

    return int(round(weighted_score_sum / total_weights))

