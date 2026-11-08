from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from app.llm.gateway import BifrostGatewayClient, GatewayStatsCollector
from app.pipeline.scoring import calculate_claim_freshness
from app.schemas import Claim, Evidence, ScoreBreakdown, Verdict

JUDGE_SYSTEM_PROMPT = """You are an authoritative fact-checking judge in a live verification pipeline.
Your job is to determine whether a claimed value in an AI-generated answer is CURRENT, OUTDATED, PARTIALLY OUTDATED, or UNVERIFIABLE based strictly on the provided live web evidence.

Rules:
1. Compare `claim.claimed_value` and `claim.text` against the numbered evidence snippets.
2. If evidence confirms the claimed value is still current and in effect, verdict is "current".
3. If evidence confirms the claimed value has been changed, superseded, struck down, or discontinued, verdict is "outdated". You MUST provide the accurate `current_value`.
4. If the claim is partially true but contains outdated details, verdict is "partially_outdated". Provide the updated `current_value`.
5. If evidence is missing, unrelated, or conflicting without consensus, verdict is "unverifiable" and `current_value` is null.
6. `explanation`: Write 1-2 clear, objective sentences explaining the verdict and quoting the specific supporting evidence.
7. `confidence`: A float between 0.0 and 1.0 representing your certainty.
8. `supporting_evidence_indices`: List of 0-based indices of the evidence items that support your verdict.

Return ONLY valid JSON matching:
{
  "verdict": "current" | "outdated" | "partially_outdated" | "unverifiable" | "skipped",
  "current_value": string or null,
  "explanation": string,
  "confidence": float (0..1),
  "supporting_evidence_indices": [int, ...]
}
"""


class RawJudgeOutput(BaseModel):
    verdict: Verdict
    current_value: Optional[str] = None
    explanation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence_indices: List[int] = Field(default_factory=list)


async def judge_claim(
    claim: Claim,
    evidence: List[Evidence],
    gateway: Optional[BifrostGatewayClient] = None,
    stats_collector: Optional[GatewayStatsCollector] = None,
) -> tuple[Verdict, Optional[str], str, ScoreBreakdown, int]:
    """Runs the judge model to evaluate a claim, then deterministically calculates freshness score."""
    # If not time sensitive, mark skipped
    if not claim.is_time_sensitive:
        freshness, breakdown, _ = calculate_claim_freshness(
            claim=claim,
            verdict="skipped",
            evidence=[],
            judge_confidence=1.0,
        )
        return (
            "skipped",
            claim.claimed_value,
            "timeless/not time-sensitive",
            breakdown,
            freshness,
        )

    # If no evidence retrieved, return unverifiable with deterministic scoring
    if not evidence:
        freshness, breakdown, _ = calculate_claim_freshness(
            claim=claim,
            verdict="unverifiable",
            evidence=[],
            judge_confidence=0.3,
        )
        return (
            "unverifiable",
            None,
            "No live evidence could be retrieved to substantiate or refute the claim.",
            breakdown,
            freshness,
        )

    client = gateway or BifrostGatewayClient()

    # Format evidence snippets for prompt
    evidence_blocks = []
    for i, ev in enumerate(evidence):
        snippet_text = ev.snippet.replace("\n", " ").strip()[:800]
        evidence_blocks.append(
            f"[{i}] URL: {ev.url}\n    Title: {ev.title}\n    Published: {ev.published_date or 'N/A'}\n    Snippet: {snippet_text}"
        )
    formatted_evidence = "\n\n".join(evidence_blocks)

    user_prompt = (
        f"Claim to Verify:\n"
        f"- Entity: {claim.entity}\n"
        f"- Attribute: {claim.attribute}\n"
        f"- Claimed Value: {claim.claimed_value}\n"
        f"- Claim Type: {claim.claim_type}\n"
        f"- Full Claim Text: \"{claim.text}\"\n\n"
        f"Live Web Evidence:\n"
        f"{formatted_evidence}\n\n"
        f"Evaluate whether the claim is current, outdated, partially_outdated, or unverifiable."
    )

    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw_output: RawJudgeOutput = await client.call_structured(
        task="judge",
        messages=messages,
        response_model=RawJudgeOutput,
        stats_collector=stats_collector,
        temperature=0.0,
    )

    # Compute freshness score and ScoreBreakdown deterministically in code
    freshness, breakdown, low_conf_flag = calculate_claim_freshness(
        claim=claim,
        verdict=raw_output.verdict,
        evidence=evidence,
        judge_confidence=raw_output.confidence,
        supporting_indices=raw_output.supporting_evidence_indices,
    )

    explanation = raw_output.explanation
    if low_conf_flag and raw_output.verdict == "unverifiable" and "confidence" not in explanation.lower():
        explanation = f"{explanation} (Flagged low confidence verification)."

    return (
        raw_output.verdict,
        raw_output.current_value,
        explanation,
        breakdown,
        freshness,
    )
