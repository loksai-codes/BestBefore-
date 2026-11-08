# BestBefore — FalkorDB Cloud Persistence & Bi-Temporal Fact Layer

## Architecture Overview

**BestBefore** integrates with a hosted **FalkorDB Cloud** instance as an authoritative knowledge graph and bi-temporal memory layer.

Instead of re-verifying every claim against the live web on every request, the graph persistence layer:
1. **Tracks Historical Evolution**: Maintains bi-temporal timelines of factual claims as they change over time.
2. **Short-Circuits Search**: Caches fresh verifications to save latency, API tokens, and Tavily rate limits.
3. **Preserves Source Lineage**: Connects facts to sources and verifications for full explainability.
4. **Degrades Gracefully**: If the remote FalkorDB instance is unreachable or network drops occur, the verification pipeline continues operating without failure, setting `graph_available = false`.

---

## Graph Schema

### Nodes
- **`(:Entity)`**: Factual entity under verification.
  - `name`: Human-readable name (e.g., `"OpenAI GPT-4"`).
  - `normalized_name`: Normalized lowercase identifier (e.g., `"openai gpt-4"`).
- **`(:Attribute)`**: Attribute of an entity.
  - `name`: Attribute name (e.g., `"pricing"`, `"ceo"`).
  - `entity`: Normalized entity identifier scoping this attribute.
- **`(:Fact)`**: Concrete factual statement and its validity window.
  - `id`: Unique identifier (e.g., `"fact-123"`).
  - `value`: Factual value (e.g., `"GPT-4o at $2.50 / 1M prompt tokens"`).
  - `valid_from`: When this fact became true in the world.
  - `valid_to`: When this fact ceased to be true (or `null` if currently active).
  - `recorded_at`: When our system recorded the fact.
  - `superseded_at`: When our system recorded that this fact was superseded (or `null` if active).
  - `source_url`: URL of the primary confirming source.
  - `authority`: Authority tier (`"official"`, `"reputable"`, `"community"`, `"unknown"`).
- **`(:Source)`**: Provenance metadata for retrieved web sources.
  - `url`: Full web source URL.
  - `domain`: Domain name (e.g., `"openai.com"`).
  - `authority`: Authority tier.
- **`(:Verification)`**: Audit log of verification runs.
  - `id`: Verification request identifier.
  - `verified_at`: ISO timestamp of verification.
  - `verdict`: Verdict (`"current"`, `"outdated"`, `"partially_outdated"`, `"unverifiable"`).
  - `freshness_score`: Deterministic score ($0 \dots 100$).

### Relationships
- `(Entity)-[:HAS_ATTRIBUTE]->(Attribute)`
- `(Attribute)-[:HAS_FACT]->(Fact)`
- `(Fact)-[:SUPPORTED_BY]->(Source)`
- `(Fact)-[:VERIFIED_IN]->(Verification)`
- `(Fact)-[:SUPERSEDES]->(Fact)`

### Indexes
Created idempotently at application startup:
- `CREATE INDEX FOR (e:Entity) ON (e.normalized_name)`
- `CREATE INDEX FOR (f:Fact) ON (f.id)`

---

## Bi-Temporal Fact Model

We distinguish between two temporal axes:
- **Valid Time (`valid_from` / `valid_to`)**: The period during which the fact was true in the real world.
- **Transaction Time (`recorded_at` / `superseded_at`)**: The period during which our system considered this knowledge to be active.

### Superseding Facts
When a verification discovers a changed value:
1. The currently active `Fact` has its `valid_to` and `superseded_at` set to the timestamp of the new verification.
2. A new `Fact` is created with `valid_to = null` and `superseded_at = null`.
3. A `(new_fact)-[:SUPERSEDES]->(old_fact)` relationship is created.
4. Old facts are **never deleted**, preserving the historical timeline for the frontend timeline view.

---

## Scripts & Operational Commands

- **Check Cloud Connection & Stats**:
  ```bash
  python backend/scripts/check_graph.py
  ```
- **Idempotent Graph Seeding**:
  ```bash
  python backend/scripts/seed_graph.py
  ```
- **Graph Test Suite**:
  ```bash
  pytest backend/tests/test_graph.py -v
  ```

