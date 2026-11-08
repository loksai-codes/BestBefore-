"""Pipeline module for generating factual answer rewrites with inline citations.

Replaces outdated/partially-outdated claims with their verified current values while
strictly preserving unchanged factual spans, with a deterministic string-replacement fallback.
"""

import logging
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.llm.gateway import BifrostGatewayClient, GatewayStatsCollector
from app.schemas import ClaimResult

logger = logging.getLogger("rewrite")

REWRITE_SYSTEM_PROMPT = """You are an expert factual rewrite editor.
Your task is to update an AI-generated answer by replacing ONLY the outdated or partially outdated claims with their verified current values.

Rules:
1. Preserve the original sentence structure, tone, and context as closely as possible.
2. Update ONLY the specific outdated facts to their verified current values.
3. Keep all unchanged, current, or timeless facts EXACTLY intact.
4. Add inline numerical citation markers like [1], [2] immediately following each updated fact, corresponding to the provided numbered source list.
5. Do NOT hallucinate new information or add commentary.

Return ONLY valid JSON matching:
{
  "rewritten_answer": string,
  "changes_made": [string, ...]
}
"""


class RewriteLLMOutput(BaseModel):
    rewritten_answer: str
    changes_made: List[str] = Field(default_factory=list)


def build_citation_map(claim_results: List[ClaimResult]) -> Tuple[Dict[str, int], List[str]]:
    """Builds a 1-based index mapping of unique evidence URLs to citation numbers."""
    url_to_idx: Dict[str, int] = {}
    sources_list: List[str] = []

    for r in claim_results:
        for ev in r.evidence:
            if ev.url and ev.url not in url_to_idx:
                idx = len(sources_list) + 1
                url_to_idx[ev.url] = idx
                sources_list.append(ev.url)

    return url_to_idx, sources_list


def validate_rewritten_answer(
    original_answer: str,
    rewritten_answer: str,
    claim_results: List[ClaimResult],
) -> bool:
    """Validates that unchanged claim facts were preserved in the rewritten answer."""
    if not rewritten_answer or not rewritten_answer.strip():
        return False

    unchanged_claims = [
        r.claim
        for r in claim_results
        if r.verdict in ["current", "unverifiable", "skipped"]
    ]

    # Check that claimed values of current/timeless facts still appear in the rewritten text
    for c in unchanged_claims:
        val = c.claimed_value.strip()
        if len(val) >= 4 and val.lower() not in rewritten_answer.lower():
            # If the exact value is missing, check if at least a major portion of claim text remains
            sample_phrase = " ".join(c.text.split()[:4])
            if sample_phrase and sample_phrase.lower() not in rewritten_answer.lower():
                logger.warning(
                    "Validation failed: Unchanged claim value '%s' or text '%s' was deleted in LLM rewrite.",
                    val,
                    c.text,
                )
                return False

    return True


def deterministic_span_replacement(
    original_answer: str,
    claim_results: List[ClaimResult],
    url_to_idx: Dict[str, int],
) -> str:
    """Deterministic fallback: replaces outdated claim spans directly without LLM."""
    outdated_results = [
        r
        for r in claim_results
        if r.verdict in ["outdated", "partially_outdated"] and r.current_value
    ]

    if not outdated_results:
        return original_answer

    # Sort in reverse order of span_start so modifying slices doesn't shift earlier offsets
    valid_spans = [
        r
        for r in outdated_results
        if 0 <= r.claim.span_start < r.claim.span_end <= len(original_answer)
    ]

    if valid_spans:
        valid_spans.sort(key=lambda r: r.claim.span_start, reverse=True)
        rewritten = original_answer
        for r in valid_spans:
            c = r.claim
            cur_val = r.current_value or ""
            # Determine citation number if source is available
            cit_marker = ""
            if r.evidence:
                first_url = r.evidence[0].url
                if first_url in url_to_idx:
                    cit_marker = f" [{url_to_idx[first_url]}]"

            # Replace the exact span or the claimed value within the span
            span_text = rewritten[c.span_start : c.span_end]
            if c.claimed_value in span_text:
                updated_span = span_text.replace(c.claimed_value, f"{cur_val}{cit_marker}", 1)
                rewritten = rewritten[: c.span_start] + updated_span + rewritten[c.span_end :]
            else:
                rewritten = (
                    rewritten[: c.span_start]
                    + f"{cur_val}{cit_marker}"
                    + rewritten[c.span_end :]
                )
        return rewritten

    # Value-based replacement fallback if character spans are absent
    rewritten = original_answer
    for r in outdated_results:
        c = r.claim
        cur_val = r.current_value or ""
        cit_marker = ""
        if r.evidence:
            first_url = r.evidence[0].url
            if first_url in url_to_idx:
                cit_marker = f" [{url_to_idx[first_url]}]"

        if c.claimed_value and c.claimed_value in rewritten:
            rewritten = rewritten.replace(c.claimed_value, f"{cur_val}{cit_marker}", 1)

    return rewritten


async def generate_rewritten_answer(
    original_answer: str,
    claim_results: List[ClaimResult],
    gateway: Optional[BifrostGatewayClient] = None,
    stats_collector: Optional[GatewayStatsCollector] = None,
) -> Optional[str]:
    """Rewrites the answer with corrected facts and citations, with span validation and fallback."""
    outdated_results = [
        r
        for r in claim_results
        if r.verdict in ["outdated", "partially_outdated"] and r.current_value
    ]

    if not outdated_results:
        return None

    url_to_idx, sources_list = build_citation_map(claim_results)

    # Prepare instructions and prompt for LLM judge model
    updates_block = []
    for r in outdated_results:
        c = r.claim
        cit_num = ""
        if r.evidence and r.evidence[0].url in url_to_idx:
            cit_num = f" (Citation [{url_to_idx[r.evidence[0].url]}])"
        updates_block.append(
            f"- Change: \"{c.claimed_value}\" -> \"{r.current_value}\"{cit_num}\n"
            f"  Context: \"{c.text}\"\n"
            f"  Entity/Attribute: {c.entity} ({c.attribute})"
        )

    sources_block = "\n".join(f"[{i+1}] {url}" for i, url in enumerate(sources_list))

    user_prompt = (
        f"Original Answer:\n\"\"\"{original_answer}\"\"\"\n\n"
        f"Verified Factual Corrections to Apply:\n"
        + "\n".join(updates_block)
        + "\n\nAvailable Evidence Sources:\n"
        + (sources_block if sources_block else "None")
        + "\n\nRewrite the original answer applying ONLY these corrections with inline citations."
    )

    client = gateway or BifrostGatewayClient()

    try:
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        llm_output: RewriteLLMOutput = await client.call_structured(
            task="judge",
            messages=messages,
            response_model=RewriteLLMOutput,
            stats_collector=stats_collector,
            temperature=0.0,
        )

        candidate = llm_output.rewritten_answer.strip()
        # Validate that unchanged facts weren't dropped
        if validate_rewritten_answer(original_answer, candidate, claim_results):
            # Append Sources footer if citations exist and not already in text
            if sources_list and "[1]" in candidate and "Sources:" not in candidate:
                footer = "\n\nSources:\n" + "\n".join(f"[{i+1}] {url}" for i, url in enumerate(sources_list))
                candidate = f"{candidate}{footer}"
            return candidate
        else:
            logger.warning("LLM rewrite failed validation. Triggering deterministic fallback.")
    except Exception as exc:
        logger.warning("LLM rewrite call failed (%s). Triggering deterministic fallback.", exc)

    # Deterministic fallback replacement
    fallback = deterministic_span_replacement(original_answer, claim_results, url_to_idx)
    if sources_list and "[1]" in fallback and "Sources:" not in fallback:
        footer = "\n\nSources:\n" + "\n".join(f"[{i+1}] {url}" for i, url in enumerate(sources_list))
        fallback = f"{fallback}{footer}"
    return fallback

