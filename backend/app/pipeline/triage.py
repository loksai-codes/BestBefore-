from typing import List, Optional
from app.schemas import Claim, VerifyOptions

CRITICAL_CLAIM_TYPES = {
    "pricing",
    "api_version",
    "leadership",
    "regulation",
    "product_release",
}

VOLATILITY_WEIGHTS = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def triage_claims(
    claims: List[Claim],
    options: Optional[VerifyOptions] = None,
) -> List[Claim]:
    """Filters and prioritizes claims based on domain criticality, volatility, and max_claims constraints.

    Rules:
    1. Always keep pricing / api_version / leadership / regulation claims (unless capped by max_claims).
    2. Drop low-volatility non-critical claims.
    3. Enforce options.max_claims (default 8), prioritized by volatility score.
    """
    max_claims = options.max_claims if (options and options.max_claims is not None) else 8

    filtered: List[Claim] = []
    for claim in claims:
        is_critical_type = claim.claim_type in CRITICAL_CLAIM_TYPES

        # Rule: Always keep critical types
        if is_critical_type:
            filtered.append(claim)
            continue

        # Rule: Drop low-volatility non-critical claims
        if claim.volatility == "low" and not claim.is_time_sensitive:
            continue

        filtered.append(claim)

    # Sort prioritized by:
    # 1. Volatility score (high > medium > low)
    # 2. Time sensitivity (time_sensitive first)
    # 3. Critical type priority
    def priority_key(c: Claim) -> tuple[int, int, int]:
        vol_score = VOLATILITY_WEIGHTS.get(c.volatility, 1)
        time_score = 1 if c.is_time_sensitive else 0
        crit_score = 1 if c.claim_type in CRITICAL_CLAIM_TYPES else 0
        return (vol_score, crit_score, time_score)

    sorted_claims = sorted(filtered, key=priority_key, reverse=True)

    return sorted_claims[:max_claims]

