# BestBefore — Architecture Overview

## System Flow

BestBefore takes an LLM-generated text answer, extracts factual assertions, verifies them against live authoritative web data, and stamps each claim with an empirical freshness score and best-before date.

```mermaid
flowchart TD
    A[LLM Answer Input] --> B[1. Claim Extraction<br/>Bifrost / Fast Model]
    B --> C[2. Triage & Volatility<br/>Policy Rules Engine]
    C -->|Timeless Fact| D1[Skip Search<br/>Freshness = 100%]
    C -->|Time-Sensitive| D2[3. FalkorDB Cloud<br/>Cache & Timeline Check]
    D2 -->|Cache Hit| E1[Return Stored Verification]
    D2 -->|Cache Miss| E2[4. Tavily Live Search<br/>Targeted Queries & Domain Filtering]
    E2 --> F[5. Tavily Extract<br/>Full Official Page Content]
    F --> G[6. LLM Judge<br/>Bifrost / Strong Model]
    G --> H[7. Deterministic Scoring<br/>Authority + Recency + Agreement]
    H --> I[8. FalkorDB Cloud Upsert<br/>Bi-Temporal Graph History]
    I --> J[9. Factual Rewrite<br/>Span Replacement / Citations]
    J --> K[JSON / SSE Stream Response]
```

---

## Component Boundaries

### 1. Frontend (`/frontend`)
- **Next.js 14 App Router** + **TypeScript** + **Tailwind CSS**.
- Real-time **Server-Sent Events (SSE)** consumer updating pipeline stepper and claim cards progressively.
- Interactive highlighted answer pane with bidirectional hover highlighting to claim cards.
- Expiry badge stamps (`FRESH`, `PARTLY STALE`, `STALE`, `TIMELESS`, `UNVERIFIED`).
- Gateway telemetry monitor, diff viewer, and export options (JSON / Markdown).

### 2. Backend (`/backend`)
- **FastAPI** + **Pydantic v2** + **pydantic-settings**.
- Pipeline stages:
  - `app/pipeline/extract.py`: Claims parser with character offset recovery.
  - `app/pipeline/triage.py`: Time-sensitivity & volatility classifier.
  - `app/pipeline/verify.py`: Tavily search engine with depth policies & full page extract.
  - `app/pipeline/judge.py`: Evidence cross-verifier with Pydantic JSON validation.
  - `app/pipeline/scoring.py`: Deterministic math formula with recency decay half-lives.
  - `app/pipeline/rewrite.py`: Citation-preserving corrected answer generator.

### 3. Persistence Layer (`/backend/app/graph/`)
- Remote hosted **FalkorDB Cloud** graph database (`bestbefore`).
- Bi-temporal fact tracking (`valid_from`/`valid_to` vs `recorded_at`/`superseded_at`).
- Automatic graceful degradation: If remote cloud database drops, requests succeed with `graph_available=false`.

### 4. AI Gateway (`/infra/` & `/backend/app/llm/gateway.py`)
- **Bifrost by Maxim AI** Docker gateway container running on `localhost:8080`.
- Task-specific model routing (`extract` -> LLaMA 3.1 8B, `judge` -> LLaMA 3.3 70B).
- Automatic fallback chain to direct Groq API endpoint if gateway container is stopped.
- Request-scoped metrics aggregation for tokens, cost, latency, and cache hits.

