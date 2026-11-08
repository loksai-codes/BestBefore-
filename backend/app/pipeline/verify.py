import asyncio
from datetime import datetime, timezone
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import KNOWN_ENTITY_DOMAINS, SEARCH_POLICIES, settings
from app.graph.client import get_graph_store
from app.llm.gateway import BifrostGatewayClient, GatewayStatsCollector
from app.pipeline.cache import tavily_cache
from app.pipeline.judge import judge_claim
from app.pipeline.scoring import calculate_claim_freshness
from app.schemas import Authority, Claim, ClaimHistoryEntry, ClaimResult, Evidence, ScoreBreakdown

REPUTABLE_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "nytimes.com",
    "apnews.com",
    "techcrunch.com",
    "theverge.com",
    "wired.com",
    "arstechnica.com",
    "cnbc.com",
    "forbes.com",
    "ft.com",
    "wikipedia.org",
    "bbc.com",
}

COMMUNITY_DOMAINS = {
    "reddit.com",
    "stackoverflow.com",
    "medium.com",
    "dev.to",
    "news.ycombinator.com",
    "quora.com",
    "substack.com",
    "x.com",
    "twitter.com",
}


def query_builder(claim: Claim) -> List[str]:
    """Builds 1-2 targeted search queries from entity, attribute, and claim type."""
    current_year = datetime.now().year
    entity = claim.entity.strip()
    attr = claim.attribute.strip()
    c_type = claim.claim_type

    queries: List[str] = []

    if c_type == "pricing":
        queries.append(f"{entity} {attr} pricing official {current_year}")
        queries.append(f"{entity} API pricing page {current_year}")
    elif c_type == "api_version":
        queries.append(f"{entity} latest version release notes {current_year}")
        queries.append(f"{entity} system requirements documentation")
    elif c_type == "leadership":
        queries.append(f"{entity} CEO {attr} announcement {current_year}")
        queries.append(f"{entity} leadership executive profile")
    elif c_type == "regulation":
        queries.append(f"{entity} {attr} court ruling status {current_year}")
        queries.append(f"{entity} regulation effective date official")
    elif c_type == "product_release":
        queries.append(f"{entity} {attr} release date {current_year}")
        queries.append(f"{entity} announcement official")
    else:
        queries.append(f"{entity} {attr} {current_year}")

    return queries[:2]


def infer_entity_domain(entity: str) -> Optional[str]:
    """Infers official domain for an entity from known entities list or heuristics."""
    lowered = entity.lower()
    for name, domain in KNOWN_ENTITY_DOMAINS.items():
        if name in lowered or lowered in name:
            return domain
    return None


def extract_domain(url: str) -> str:
    """Extracts base registered domain from a URL."""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return "unknown"


def classify_authority(url: str, entity: str) -> Authority:
    """Classifies source authority: official | reputable | community | unknown."""
    domain = extract_domain(url)
    known_official = infer_entity_domain(entity)

    # 1. Official domain check
    if known_official and (domain == known_official or domain.endswith("." + known_official)):
        return "official"

    # Government / EU official gazette checks
    if domain.endswith(".gov") or domain.endswith(".europa.eu") or domain.endswith(".mil"):
        return "official"

    # Docs / Developer portals
    if domain.startswith("docs.") or domain.startswith("developer.") or "official" in domain:
        return "official"

    # 2. Reputable news / press
    for rep in REPUTABLE_DOMAINS:
        if domain == rep or domain.endswith("." + rep):
            return "reputable"

    # 3. Community forums
    for com in COMMUNITY_DOMAINS:
        if domain == com or domain.endswith("." + com):
            return "community"

    return "unknown"


def parse_date_fallback(text: str) -> Optional[str]:
    """Attempts to parse YYYY-MM-DD from text if metadata missing."""
    match = re.search(r"\b(202[0-9]-[0-1][0-9]-[0-3][0-9])\b", text)
    if match:
        return match.group(1)
    return None


class VerificationEngine:
    """Orchestrates search, page extraction, evidence building, and LLM judgment."""

    def __init__(
        self,
        tavily_client: Optional[TavilyClient] = None,
        gateway: Optional[BifrostGatewayClient] = None,
        concurrency_limit: int = 4,
        graph_store: Optional[Any] = None,
    ) -> None:
        self.tavily = tavily_client or (
            TavilyClient(api_key=settings.TAVILY_API_KEY)
            if settings.TAVILY_API_KEY
            else None
        )
        self.gateway = gateway or BifrostGatewayClient()
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.graph_store = (
            graph_store
            if graph_store is not None
            else (get_graph_store() if settings.FALKORDB_HOST else None)
        )

    async def _execute_search(
        self, query: str, claim: Claim, policy: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Executes a cached search via Tavily in a worker thread."""
        cache_key = {"query": query, "type": claim.claim_type}
        cached = tavily_cache.get("search", cache_key)
        if cached:
            return cached

        if not self.tavily:
            return []

        # Prepare domains
        include_domains = list(policy.get("include_domains", []))
        if policy.get("prefer_official", True):
            known = infer_entity_domain(claim.entity)
            if known and known not in include_domains:
                include_domains.append(known)

        search_kwargs: Dict[str, Any] = {
            "query": query,
            "search_depth": policy.get("search_depth", "advanced"),
            "max_results": 3,
        }

        topic = policy.get("topic")
        if topic and topic in ["general", "news"]:
            search_kwargs["topic"] = topic

        days = policy.get("days")
        if days and claim.volatility == "high":
            search_kwargs["days"] = days

        if include_domains:
            search_kwargs["include_domains"] = include_domains[:5]

        try:
            resp = await asyncio.to_thread(self.tavily.search, **search_kwargs)
            results = resp.get("results", [])
            tavily_cache.set("search", cache_key, results)
            return results
        except Exception:
            return []

    async def _execute_extract(self, urls: List[str]) -> Dict[str, str]:
        """Extracts full web page contents for the top URLs via Tavily Extract."""
        if not self.tavily or not urls:
            return {}

        extracted_map: Dict[str, str] = {}
        missing_urls = []

        for u in urls:
            cached_content = tavily_cache.get("extract", u)
            if cached_content:
                extracted_map[u] = cached_content
            else:
                missing_urls.append(u)

        if not missing_urls:
            return extracted_map

        try:
            resp = await asyncio.to_thread(
                self.tavily.extract,
                urls=missing_urls[:2],
                extract_depth="basic",
                format="markdown",
            )
            for item in resp.get("results", []):
                u = item.get("url")
                raw = item.get("raw_content", "")
                if u and raw:
                    trimmed = raw.strip()[:2500]  # Trimmed content for LLM context
                    extracted_map[u] = trimmed
                    tavily_cache.set("extract", u, trimmed)
        except Exception:
            pass

        return extracted_map

    async def verify_single_claim(
        self,
        claim: Claim,
        stats_collector: Optional[GatewayStatsCollector] = None,
        timings: Optional[Dict[str, float]] = None,
    ) -> ClaimResult:
        """Verifies an individual claim with error isolation and timeout protection."""
        # Timeless facts bypass live web search
        if not claim.is_time_sensitive:
            t_s0 = time.perf_counter()
            verdict, current_val, expl, breakdown, freshness = await judge_claim(
                claim, [], gateway=self.gateway, stats_collector=stats_collector
            )
            if timings is not None:
                timings["score"] = timings.get("score", 0.0) + (time.perf_counter() - t_s0) * 1000
            return ClaimResult(
                claim=claim,
                verdict=verdict,
                freshness_score=freshness,
                current_value=current_val,
                explanation=expl,
                evidence=[],
                breakdown=breakdown,
                history=[
                    ClaimHistoryEntry(
                        value=claim.claimed_value,
                        valid_from=None,
                        verified_at=datetime.now(timezone.utc).isoformat(),
                    )
                ],
            )

        # Check knowledge graph cache first to short-circuit Tavily search
        t_gl0 = time.perf_counter()
        if self.graph_store and self.graph_store.is_available:
            try:
                cached_res = await self.graph_store.get_recent_verification(
                    entity=claim.entity,
                    attribute=claim.attribute,
                    volatility=claim.volatility,
                )
                if timings is not None:
                    timings["graph_lookup"] = timings.get("graph_lookup", 0.0) + (time.perf_counter() - t_gl0) * 1000
                if cached_res:
                    if stats_collector:
                        stats_collector.record_cache_hit()
                    cached_res.claim = claim
                    return cached_res
            except Exception as exc:
                logger.warning("Graph cache check failed, falling back to search: %s", exc)
        if timings is not None and "graph_lookup" not in timings:
            timings["graph_lookup"] = timings.get("graph_lookup", 0.0) + (time.perf_counter() - t_gl0) * 1000

        async with self.semaphore:
            try:
                # 15 second timeout per claim
                return await asyncio.wait_for(
                    self._verify_claim_core(claim, stats_collector=stats_collector, timings=timings),
                    timeout=15.0,
                )
            except Exception as exc:
                # Per-claim error isolation: failure on 1 claim must not fail request
                return self._build_fallback_result(
                    claim, f"Verification skipped or timed out: {exc.__class__.__name__}"
                )

    async def _verify_claim_core(
        self,
        claim: Claim,
        stats_collector: Optional[GatewayStatsCollector] = None,
        timings: Optional[Dict[str, float]] = None,
    ) -> ClaimResult:
        t_v0 = time.perf_counter()
        queries = query_builder(claim)
        policy = SEARCH_POLICIES.get(claim.claim_type, SEARCH_POLICIES["other"])

        # Execute searches across the 1-2 queries
        search_tasks = [self._execute_search(q, claim, policy) for q in queries]
        search_results_nested = await asyncio.gather(*search_tasks, return_exceptions=True)

        raw_results: List[Dict[str, Any]] = []
        seen_urls = set()
        for res_list in search_results_nested:
            if isinstance(res_list, list):
                for item in res_list:
                    u = item.get("url")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        raw_results.append(item)

        # Top 2 URLs for Tavily Extract
        top_urls = [r["url"] for r in raw_results[:2] if "url" in r]
        extracted_content = await self._execute_extract(top_urls)

        # Build Evidence objects
        evidence_list: List[Evidence] = []
        for r in raw_results[:4]:
            url = r.get("url", "")
            if not url:
                continue

            domain = extract_domain(url)
            authority = classify_authority(url, claim.entity)
            title = r.get("title", domain)

            # Prefer extracted trimmed content, fallback to search snippet
            snippet = extracted_content.get(url) or r.get("content", "")
            pub_date = r.get("published_date") or parse_date_fallback(snippet)

            evidence_list.append(
                Evidence(
                    url=url,
                    title=title,
                    domain=domain,
                    snippet=snippet[:1200],
                    published_date=pub_date,
                    authority=authority,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        # Run Judge step
        t_j0 = time.perf_counter()
        verdict, current_val, expl, breakdown, freshness = await judge_claim(
            claim=claim,
            evidence=evidence_list,
            gateway=self.gateway,
            stats_collector=stats_collector,
        )
        if timings is not None:
            timings["verify"] = timings.get("verify", 0.0) + (time.perf_counter() - t_v0) * 1000
            timings["score"] = timings.get("score", 0.0) + (time.perf_counter() - t_j0) * 1000

        # Retrieve historical timeline facts from knowledge graph
        history_items: List[ClaimHistoryEntry] = []
        if self.graph_store and self.graph_store.is_available:
            try:
                history_items = await self.graph_store.get_history(claim.entity, claim.attribute)
            except Exception:
                history_items = []

        if not history_items and current_val:
            history_items.append(
                ClaimHistoryEntry(
                    value=current_val,
                    valid_from=None,
                    verified_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        claim_result = ClaimResult(
            claim=claim,
            verdict=verdict,
            freshness_score=freshness,
            current_value=current_val,
            explanation=expl,
            evidence=evidence_list,
            breakdown=breakdown,
            history=history_items,
        )

        # Upsert verification to FalkorDB Cloud
        t_gw0 = time.perf_counter()
        if self.graph_store and self.graph_store.is_available:
            try:
                await self.graph_store.upsert_verification(claim, claim_result)
            except Exception as exc:
                logger.warning("Failed to persist verification to FalkorDB: %s", exc)
        if timings is not None:
            timings["graph_write"] = timings.get("graph_write", 0.0) + (time.perf_counter() - t_gw0) * 1000

        return claim_result

    def _build_fallback_result(self, claim: Claim, reason: str) -> ClaimResult:
        """Returns safe unverifiable ClaimResult on isolated failure."""
        score, breakdown, _ = calculate_claim_freshness(
            claim=claim,
            verdict="unverifiable",
            evidence=[],
            judge_confidence=0.0,
        )
        return ClaimResult(
            claim=claim,
            verdict="unverifiable",
            freshness_score=score,
            current_value=None,
            explanation=f"{reason} (Flagged low confidence).",
            evidence=[],
            breakdown=breakdown,
            history=[],
        )

    async def verify_claims(
        self,
        claims: List[Claim],
        stats_collector: Optional[GatewayStatsCollector] = None,
        timings: Optional[Dict[str, float]] = None,
    ) -> List[ClaimResult]:
        """Concurrently verifies a list of claims with semaphore-controlled concurrency."""
        tasks = [
            self.verify_single_claim(claim, stats_collector=stats_collector, timings=timings)
            for claim in claims
        ]
        return await asyncio.gather(*tasks)
