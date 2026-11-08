import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import redis.exceptions
from falkordb import FalkorDB, Graph

from app.config import settings
from app.schemas import (
    Claim,
    ClaimHistoryEntry,
    ClaimResult,
    Evidence,
    ScoreBreakdown,
    Verdict,
)

logger = logging.getLogger("graph_store")

VOLATILITY_CACHE_TTL_DAYS = {
    "high": 3,
    "medium": 14,
    "low": 60,
}


class GraphStore:
    """FalkorDB persistence layer managing bi-temporal fact tracking,

    source provenance, and verification caching.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ssl: Optional[bool] = None,
        graph_name: Optional[str] = None,
        socket_timeout: int = 5,
        connect_timeout: int = 5,
    ):
        self.host = host or settings.FALKORDB_HOST
        self.port = port or settings.FALKORDB_PORT or 6379
        self.username = username or settings.FALKORDB_USERNAME
        self.password = password or settings.FALKORDB_PASSWORD
        self.ssl = ssl if ssl is not None else settings.FALKORDB_SSL
        self.graph_name = graph_name or settings.FALKORDB_GRAPH
        self.socket_timeout = socket_timeout
        self.connect_timeout = connect_timeout

        self._db: Optional[FalkorDB] = None
        self._graph: Optional[Graph] = None
        self._is_available: bool = False

    @property
    def is_available(self) -> bool:
        return self._is_available and self._graph is not None

    def connect_sync(self) -> bool:
        """Establishes connection to FalkorDB Cloud instance synchronously."""
        if not self.host:
            logger.warning("FALKORDB_HOST not configured. Graph persistence disabled.")
            self._is_available = False
            return False

        try:
            self._db = FalkorDB(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                ssl=self.ssl,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.connect_timeout,
            )
            self._graph = self._db.select_graph(self.graph_name)

            # Test connectivity with ping / ping-check
            res = self._graph.query("RETURN 1 AS ping")
            if res and res.result_set:
                self._is_available = True
                self._ensure_indexes_sync()
                logger.info(
                    "Connected to FalkorDB Cloud graph '%s' at %s:%s",
                    self.graph_name,
                    self.host,
                    self.port,
                )
                return True
        except Exception as exc:
            logger.warning(
                "FalkorDB Cloud connection failed: %s (%s). Operating in degraded mode.",
                exc.__class__.__name__,
                exc,
            )
            self._is_available = False
            return False

        return False

    async def connect(self) -> bool:
        """Async wrapper to establish connection in threadpool."""
        return await asyncio.to_thread(self.connect_sync)

    def _ensure_indexes_sync(self) -> None:
        """Ensures indexes exist on Entity.normalized_name and Fact.id (idempotent)."""
        if not self._graph:
            return
        try:
            self._graph.query("CREATE INDEX FOR (e:Entity) ON (e.normalized_name)")
        except Exception:
            pass
        try:
            self._graph.query("CREATE INDEX FOR (f:Fact) ON (f.id)")
        except Exception:
            pass

    def _query_sync_with_retry(
        self, query: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 2
    ) -> Any:
        """Executes a Cypher query with retry and backoff on transient network faults."""
        if not self._graph:
            return None

        delay = 0.5
        for attempt in range(max_retries + 1):
            try:
                return self._graph.query(query, params=params)
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as net_err:
                if attempt == max_retries:
                    logger.warning("FalkorDB query failed after %d retries: %s", max_retries, net_err)
                    self._is_available = False
                    return None
                time.sleep(delay)
                delay *= 2
            except Exception as err:
                logger.warning("FalkorDB query error: %s (%s)", err.__class__.__name__, err)
                return None

        return None

    async def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Runs query in threadpool to prevent blocking the event loop."""
        if not self.is_available:
            return None
        return await asyncio.to_thread(self._query_sync_with_retry, query, params)

    async def health_check(self) -> bool:
        """Probes whether the FalkorDB graph is reachable and responsive."""
        if not self.host:
            return False
        try:
            res = await self.query("RETURN 1 AS health")
            return bool(res and res.result_set)
        except Exception:
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """Returns node count statistics for the graph."""
        if not self.is_available:
            return {"available": False, "nodes": 0, "facts": 0}

        try:
            q = """
            MATCH (n)
            RETURN count(n) AS total_nodes
            """
            res = await self.query(q)
            total = res.result_set[0][0] if (res and res.result_set) else 0

            q_facts = """
            MATCH (f:Fact)
            RETURN count(f) AS total_facts
            """
            res_facts = await self.query(q_facts)
            facts = res_facts.result_set[0][0] if (res_facts and res_facts.result_set) else 0

            return {"available": True, "nodes": total, "facts": facts, "graph": self.graph_name}
        except Exception:
            return {"available": False, "nodes": 0, "facts": 0}

    async def upsert_verification(self, claim: Claim, result: ClaimResult) -> None:
        """Upserts a verification result into the graph with bi-temporal semantics:

        - Creates Entity and Attribute nodes if they don't exist.
        - Records Verification node.
        - If active Fact matches current value -> links to Verification.
        - If active Fact has changed -> supersedes old Fact (valid_to=now, superseded_at=now),
          creates new Fact, links with SUPERSEDES relationship.
        - Attaches Sources with SUPPORTED_BY relationships.
        """
        if not self.is_available:
            return

        norm_entity = claim.entity.strip().lower()
        entity_name = claim.entity.strip()
        norm_attr = claim.attribute.strip().lower()

        # Target value for the fact
        current_val = (
            result.current_value
            if (result.current_value and result.verdict in ["outdated", "partially_outdated"])
            else claim.claimed_value
        )
        if not current_val:
            current_val = claim.claimed_value

        now_iso = datetime.now(timezone.utc).isoformat()
        new_fact_id = f"fact-{uuid.uuid4()}"
        verification_id = claim.id or f"verif-{uuid.uuid4()}"

        # Valid from is published date of primary evidence if available, else now
        valid_from = None
        primary_source_url = None
        primary_authority = "unknown"
        sources_param = []

        if result.evidence:
            first_ev = result.evidence[0]
            valid_from = first_ev.published_date or now_iso
            primary_source_url = first_ev.url
            primary_authority = first_ev.authority
            for ev in result.evidence[:4]:
                sources_param.append({
                    "url": ev.url,
                    "domain": ev.domain,
                    "authority": ev.authority,
                })
        else:
            valid_from = now_iso

        upsert_cypher = """
        MERGE (e:Entity {normalized_name: $norm_entity})
        ON CREATE SET e.name = $entity_name
        MERGE (e)-[:HAS_ATTRIBUTE]->(a:Attribute {name: $norm_attr, entity: $norm_entity})

        CREATE (v:Verification {
            id: $v_id,
            verified_at: $now_iso,
            verdict: $verdict,
            freshness_score: $freshness_score
        })

        WITH a, v
        OPTIONAL MATCH (a)-[:HAS_FACT]->(old_f:Fact)
        WHERE old_f.valid_to IS NULL AND old_f.superseded_at IS NULL

        // Case 1: active fact exists and value matches current value
        FOREACH (_ IN CASE WHEN old_f IS NOT NULL AND old_f.value = $current_val THEN [1] ELSE [] END |
            MERGE (old_f)-[:VERIFIED_IN]->(v)
        )

        // Case 2: active fact exists but value changed -> supersede old fact
        FOREACH (_ IN CASE WHEN old_f IS NOT NULL AND old_f.value <> $current_val THEN [1] ELSE [] END |
            SET old_f.valid_to = $now_iso, old_f.superseded_at = $now_iso
        )
        FOREACH (_ IN CASE WHEN old_f IS NOT NULL AND old_f.value <> $current_val THEN [1] ELSE [] END |
            CREATE (new_f:Fact {
                id: $new_fact_id,
                value: $current_val,
                valid_from: $valid_from,
                valid_to: null,
                recorded_at: $now_iso,
                superseded_at: null,
                source_url: $primary_source_url,
                authority: $primary_authority
            })
            MERGE (a)-[:HAS_FACT]->(new_f)
            CREATE (new_f)-[:SUPERSEDES]->(old_f)
            MERGE (new_f)-[:VERIFIED_IN]->(v)
        )

        // Case 3: no active fact existed previously -> create initial fact
        FOREACH (_ IN CASE WHEN old_f IS NULL THEN [1] ELSE [] END |
            CREATE (new_f:Fact {
                id: $new_fact_id,
                value: $current_val,
                valid_from: $valid_from,
                valid_to: null,
                recorded_at: $now_iso,
                superseded_at: null,
                source_url: $primary_source_url,
                authority: $primary_authority
            })
            MERGE (a)-[:HAS_FACT]->(new_f)
            MERGE (new_f)-[:VERIFIED_IN]->(v)
        )
        """

        params = {
            "norm_entity": norm_entity,
            "entity_name": entity_name,
            "norm_attr": norm_attr,
            "v_id": verification_id,
            "now_iso": now_iso,
            "verdict": result.verdict,
            "freshness_score": result.freshness_score,
            "current_val": current_val,
            "new_fact_id": new_fact_id,
            "valid_from": valid_from,
            "primary_source_url": primary_source_url,
            "primary_authority": primary_authority,
        }

        await self.query(upsert_cypher, params)

        # Attach sources to active fact if any
        if sources_param:
            sources_cypher = """
            MATCH (a:Attribute {name: $norm_attr, entity: $norm_entity})<-[:HAS_ATTRIBUTE]-(e:Entity {normalized_name: $norm_entity})
            MATCH (a)-[:HAS_FACT]->(f:Fact)
            WHERE f.valid_to IS NULL AND f.superseded_at IS NULL
            UNWIND $sources AS src
            MERGE (s:Source {url: src.url})
            ON CREATE SET s.domain = src.domain, s.authority = src.authority
            MERGE (f)-[:SUPPORTED_BY]->(s)
            """
            await self.query(
                sources_cypher,
                {
                    "norm_entity": norm_entity,
                    "norm_attr": norm_attr,
                    "sources": sources_param,
                },
            )

    async def get_history(self, entity: str, attribute: str) -> List[ClaimHistoryEntry]:
        """Returns chronological list of facts recorded for this entity and attribute."""
        if not self.is_available:
            return []

        norm_entity = entity.strip().lower()
        norm_attr = attribute.strip().lower()

        cypher = """
        MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FACT]->(f:Fact)
        WHERE e.normalized_name = $norm_entity AND a.name = $norm_attr
        OPTIONAL MATCH (f)-[:VERIFIED_IN]->(v:Verification)
        RETURN f.value, f.valid_from, f.valid_to, f.recorded_at, f.superseded_at, v.verified_at
        ORDER BY f.recorded_at ASC
        """
        res = await self.query(cypher, {"norm_entity": norm_entity, "norm_attr": norm_attr})
        if not res or not res.result_set:
            return []

        entries: List[ClaimHistoryEntry] = []
        for row in res.result_set:
            val = str(row[0]) if row[0] is not None else ""
            valid_from = str(row[1]) if row[1] is not None else None
            recorded_at = str(row[3]) if row[3] is not None else None
            verified_at = str(row[5]) if row[5] is not None else recorded_at

            entries.append(
                ClaimHistoryEntry(
                    value=val,
                    valid_from=valid_from,
                    verified_at=verified_at,
                )
            )

        return entries

    async def as_of(self, entity: str, attribute: str, date_str: str) -> Optional[Dict[str, Any]]:
        """Bi-temporal as-of query: returns the fact that was valid at a specific point in time."""
        if not self.is_available:
            return None

        norm_entity = entity.strip().lower()
        norm_attr = attribute.strip().lower()

        cypher = """
        MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FACT]->(f:Fact)
        WHERE e.normalized_name = $norm_entity AND a.name = $norm_attr
          AND (f.valid_from IS NULL OR f.valid_from <= $as_of_date)
          AND (f.valid_to IS NULL OR f.valid_to > $as_of_date)
        RETURN f.id, f.value, f.valid_from, f.valid_to, f.recorded_at, f.source_url, f.authority
        ORDER BY f.recorded_at DESC
        LIMIT 1
        """
        res = await self.query(
            cypher,
            {
                "norm_entity": norm_entity,
                "norm_attr": norm_attr,
                "as_of_date": date_str,
            },
        )
        if not res or not res.result_set:
            return None

        row = res.result_set[0]
        return {
            "fact_id": row[0],
            "value": row[1],
            "valid_from": row[2],
            "valid_to": row[3],
            "recorded_at": row[4],
            "source_url": row[5],
            "authority": row[6],
        }

    async def get_recent_verification(
        self,
        entity: str,
        attribute: str,
        volatility: str = "medium",
    ) -> Optional[ClaimResult]:
        """Checks if a fresh verification exists in the graph to short-circuit Tavily search."""
        if not self.is_available:
            return None

        norm_entity = entity.strip().lower()
        norm_attr = attribute.strip().lower()
        ttl_days = VOLATILITY_CACHE_TTL_DAYS.get(volatility, 14)

        cypher = """
        MATCH (e:Entity)-[:HAS_ATTRIBUTE]->(a:Attribute)-[:HAS_FACT]->(f:Fact)-[:VERIFIED_IN]->(v:Verification)
        WHERE e.normalized_name = $norm_entity AND a.name = $norm_attr
          AND f.valid_to IS NULL AND f.superseded_at IS NULL
        OPTIONAL MATCH (f)-[:SUPPORTED_BY]->(s:Source)
        RETURN f.value, f.valid_from, f.source_url, f.authority,
               v.id, v.verified_at, v.verdict, v.freshness_score,
               s.url, s.domain, s.authority
        ORDER BY v.verified_at DESC
        LIMIT 4
        """
        res = await self.query(cypher, {"norm_entity": norm_entity, "norm_attr": norm_attr})
        if not res or not res.result_set:
            return None

        first_row = res.result_set[0]
        verified_at_str = first_row[5]
        if not verified_at_str:
            return None

        try:
            verified_dt = datetime.fromisoformat(verified_at_str.replace("Z", "+00:00"))
            cutoff_dt = datetime.now(timezone.utc) - timedelta(days=ttl_days)
            if verified_dt < cutoff_dt:
                # Cache expired
                return None
        except Exception:
            return None

        # Fresh verification exists! Build ClaimResult
        fact_val = str(first_row[0]) if first_row[0] is not None else ""
        verdict: Verdict = first_row[6]
        score = int(first_row[7])

        evidence_list: List[Evidence] = []
        seen_urls = set()
        for row in res.result_set:
            s_url = row[8]
            s_domain = row[9] or "source"
            s_auth = row[10] or "reputable"
            if s_url and s_url not in seen_urls:
                seen_urls.add(s_url)
                evidence_list.append(
                    Evidence(
                        url=s_url,
                        title=s_domain,
                        domain=s_domain,
                        snippet="Verified from authoritative knowledge graph.",
                        published_date=first_row[1],
                        authority=s_auth,
                        retrieved_at=verified_at_str,
                    )
                )

        history = await self.get_history(entity, attribute)

        # Temporary placeholder claim
        dummy_claim = Claim(
            id=first_row[4] or f"claim-{uuid.uuid4()}",
            text=f"{entity} {attribute}: {fact_val}",
            span_start=0,
            span_end=len(f"{entity} {attribute}: {fact_val}"),
            entity=entity,
            attribute=attribute,
            claimed_value=fact_val,
            claim_type="other",
            volatility=volatility,  # type: ignore
            is_time_sensitive=True,
        )

        return ClaimResult(
            claim=dummy_claim,
            verdict=verdict,
            freshness_score=score,
            current_value=fact_val,
            explanation=f"Re-verified via knowledge graph cache (verified at {verified_at_str}).",
            evidence=evidence_list,
            breakdown=ScoreBreakdown(
                source_authority=1.0,
                evidence_recency=1.0,
                source_agreement=1.0,
                verdict_confidence=0.98,
                conflict_penalty=0.0,
            ),
            history=history,
        )

    async def get_claim_history_by_id(self, claim_id: str) -> List[ClaimHistoryEntry]:
        """Resolves claim_id to its entity and attribute via graph traversal and returns history."""
        if not self.is_available:
            return []

        cypher = """
        MATCH (v:Verification {id: $claim_id})<-[:VERIFIED_IN]-(f:Fact)<-[:HAS_FACT]-(a:Attribute)<-[:HAS_ATTRIBUTE]-(e:Entity)
        RETURN e.name, a.name
        LIMIT 1
        """
        res = await self.query(cypher, {"claim_id": claim_id})
        if res and res.result_set:
            e_name = res.result_set[0][0]
            a_name = res.result_set[0][1]
            return await self.get_history(e_name, a_name)

        return []


# Global singleton GraphStore
_global_graph_store: Optional[GraphStore] = None


def get_graph_store() -> GraphStore:
    """Provides the shared GraphStore instance."""
    global _global_graph_store
    if _global_graph_store is None:
        _global_graph_store = GraphStore()
    return _global_graph_store
