import uuid
from typing import List, Literal, Optional, Tuple
from pydantic import BaseModel, Field

from app.llm.gateway import BifrostGatewayClient, GatewayStatsCollector
from app.schemas import Claim, ClaimType, Volatility

EXTRACTION_SYSTEM_PROMPT = """You are an expert fact-checking analyzer. Your job is to extract atomic factual assertions from an AI-generated answer.
For each claim, identify:
- `text`: the EXACT verbatim substring in the answer representing the assertion.
- `span_start`: 0-indexed starting character offset of `text` in the original answer.
- `span_end`: 0-indexed ending character offset of `text` in the original answer.
- `entity`: The subject entity (e.g., "OpenAI GPT-4", "Twitter", "FTC").
- `attribute`: The property asserted (e.g., "API Pricing", "CEO", "Effective Date").
- `claimed_value`: The specific asserted value (e.g., "$30.00 / 1M tokens", "Parag Agrawal", "Sept 4, 2024").
- `claim_type`: EXACTLY one of: "pricing", "api_version", "regulation", "leadership", "product_release", "other".
- `volatility`: "high" (frequently changes, e.g. prices, executives), "medium" (periodic changes, e.g. framework versions), "low" (rarely changes).
- `is_time_sensitive`: boolean. True if the claim represents current state, active status, or volatile data. False if it is a timeless historical fact or permanent truth (e.g., "Python was created in 1991").

### Few-shot Examples:

Example 1:
Input: "OpenAI GPT-4 pricing starts at $30.00 per million prompt tokens."
Output:
{
  "claims": [
    {
      "text": "GPT-4 pricing starts at $30.00 per million prompt tokens",
      "span_start": 7,
      "span_end": 63,
      "entity": "OpenAI GPT-4",
      "attribute": "Prompt Token Pricing",
      "claimed_value": "$30.00 / 1M tokens",
      "claim_type": "pricing",
      "volatility": "high",
      "is_time_sensitive": true
    }
  ]
}

Example 2:
Input: "Parag Agrawal is the CEO of Twitter, which was founded in 2006."
Output:
{
  "claims": [
    {
      "text": "Parag Agrawal is the CEO of Twitter",
      "span_start": 0,
      "span_end": 35,
      "entity": "Twitter",
      "attribute": "Chief Executive Officer",
      "claimed_value": "Parag Agrawal",
      "claim_type": "leadership",
      "volatility": "high",
      "is_time_sensitive": true
    },
    {
      "text": "founded in 2006",
      "span_start": 47,
      "span_end": 62,
      "entity": "Twitter",
      "attribute": "Founding Year",
      "claimed_value": "2006",
      "claim_type": "other",
      "volatility": "low",
      "is_time_sensitive": false
    }
  ]
}

Return ONLY valid JSON matching the schema {"claims": [...]}.
"""


class RawExtractedClaim(BaseModel):
    text: str
    span_start: int
    span_end: int
    entity: str
    attribute: str
    claimed_value: str
    claim_type: ClaimType
    volatility: Volatility
    is_time_sensitive: bool


class ExtractionResponse(BaseModel):
    claims: List[RawExtractedClaim] = Field(default_factory=list)


def align_span(
    answer: str, claim_text: str, start: int, end: int
) -> Optional[Tuple[int, int, str]]:
    """Verifies and repairs claim spans against the original text.
    Returns (start, end, exact_text) or None if unrecoverable.
    """
    if not claim_text:
        return None

    # 1. Exact match at given offsets
    if 0 <= start < end <= len(answer) and answer[start:end] == claim_text:
        return (start, end, claim_text)

    # 2. Direct verbatim search
    idx = answer.find(claim_text)
    if idx != -1:
        return (idx, idx + len(claim_text), claim_text)

    # 3. Stripped text search
    stripped = claim_text.strip()
    idx = answer.find(stripped)
    if idx != -1:
        return (idx, idx + len(stripped), stripped)

    # 4. Case-insensitive search
    idx = answer.lower().find(claim_text.lower())
    if idx != -1:
        actual_text = answer[idx : idx + len(claim_text)]
        return (idx, idx + len(claim_text), actual_text)

    return None


async def extract_claims(
    answer: str,
    gateway: Optional[BifrostGatewayClient] = None,
    stats_collector: Optional[GatewayStatsCollector] = None,
) -> List[Claim]:
    """Extracts atomic claims from text with verified character offsets."""
    text = answer.strip()
    if not text:
        return []

    client = gateway or BifrostGatewayClient()

    messages = [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Analyze and extract claims from this answer:\n\n{answer}"},
    ]

    extraction_res = await client.call_structured(
        task="extract",
        messages=messages,
        response_model=ExtractionResponse,
        stats_collector=stats_collector,
        temperature=0.0,
    )

    claims: List[Claim] = []
    for raw in extraction_res.claims:
        span_info = align_span(answer, raw.text, raw.span_start, raw.span_end)
        if not span_info:
            # Drop claims that cannot be anchored to the source text
            continue

        start, end, actual_text = span_info
        claim_id = f"claim-{uuid.uuid4().hex[:8]}"

        claims.append(
            Claim(
                id=claim_id,
                text=actual_text,
                span_start=start,
                span_end=end,
                entity=raw.entity or "Entity",
                attribute=raw.attribute or "Attribute",
                claimed_value=raw.claimed_value or actual_text,
                claim_type=raw.claim_type,
                volatility=raw.volatility,
                is_time_sensitive=raw.is_time_sensitive,
            )
        )

    return claims
