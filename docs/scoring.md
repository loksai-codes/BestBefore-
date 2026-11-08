# Freshness Scoring System

## Overview

In **BestBefore**, freshness scores are calculated **deterministically in code** from concrete empirical evidence signals, rather than being guessed or hallucinated by an LLM.

This design guarantees:
- **Reproducibility**: Identical evidence signals yield identical scores every time.
- **Auditability**: Every score component is exposed in `ScoreBreakdown` (0..1) so users and auditors can inspect why a claim scored high or low.
- **Robust Governance**: Hard caps bound the maximum possible score based on factual verdict, preventing outdated or unverifiable claims from receiving high scores.

---

## Score Components (Each Normalized to 0.0 – 1.0)

### 1. Source Authority (`source_authority`)
Measures the reliability of the retrieved evidence sources based on domain credibility:
- **Official (1.0)**: Entity official domain, official documentation portal, or government/regulatory gazettes (`.gov`, `.europa.eu`).
- **Reputable (0.75)**: Major press, tier-1 financial and tech news (`reuters.com`, `bloomberg.com`, `techcrunch.com`, `theverge.com`, `wikipedia.org`).
- **Community (0.40)**: Discussion forums and personal publishing platforms (`reddit.com`, `stackoverflow.com`, `medium.com`, `x.com`).
- **Unknown (0.20)**: Unclassified or low-reputation web domains.

Evidence items that directly support the judged verdict are assigned a higher weight multiplier (`supporting_evidence_weight = 2.5`), ensuring authoritative agreeing sources dictate the authority score.

$$\text{source\_authority} = \frac{\sum_{i} w_i \cdot \text{auth}_i}{\sum_{i} w_i}$$

---

### 2. Evidence Recency (`evidence_recency`)
Measures temporal relevance using an **exponential half-life decay** based on the claim's volatility category:

$$\text{recency}_i = 0.5^{\left(\frac{\text{age\_days}}{T_{1/2}}\right)}$$

Where the half-life $T_{1/2}$ is defined per claim volatility:
- **High Volatility ($T_{1/2} = 30\text{ days}$)**: Rapidly changing facts (e.g., API pricing, executive leadership, pending court injunctions).
- **Medium Volatility ($T_{1/2} = 180\text{ days}$)**: Periodic updates (e.g., SDK versions, software releases).
- **Low Volatility ($T_{1/2} = 730\text{ days}$)**: Slow-changing standards and long-term milestones.
- **Undated Sources**: If metadata lacks a published date, a neutral baseline of `0.40` is assigned.

---

### 3. Source Agreement (`source_agreement`)
Calculates the proportion of retrieved evidence items that substantiate the judged current value:

$$\text{source\_agreement} = \frac{\text{count of agreeing evidence items}}{\text{total retrieved evidence items}}$$

- 1.0 indicates unanimous consensus among retrieved sources.
- Lower values indicate divergent or conflicting reporting.

---

### 4. Verdict Confidence (`verdict_confidence`)
The confidence probability ($0.0 \dots 1.0$) provided by the LLM Judge model when cross-verifying the claim against the retrieved evidence texts.

---

### 5. Conflict Penalty (`conflict_penalty`)
Applies a penalty in $[0.0, 1.0]$ when sources disagree or when no official primary source could be retrieved:

$$\text{conflict\_penalty} = \min\left(1.0, (1 - \text{agreement}) \cdot (1 - \text{official\_missing\_penalty}) + \text{official\_missing\_penalty}\right)$$

Where:
- $\text{official\_missing\_penalty} = 0.35$ if no official source was retrieved, and $0.0$ if at least one official source is present.
- If all sources agree and an official source is present, $\text{conflict\_penalty} = 0.0$.
- If no evidence exists at all, $\text{conflict\_penalty} = 1.0$.

---

## Formula & Penalty Weighting

1. **Base Score Calculation**:
   $$\text{base} = 0.30 \cdot \text{source\_authority} + 0.25 \cdot \text{evidence\_recency} + 0.25 \cdot \text{source\_agreement} + 0.20 \cdot \text{verdict\_confidence}$$

2. **Conflict Penalty Application**:
   $$\text{penalized\_base} = \text{base} \cdot \left(1.0 - 0.50 \cdot \text{conflict\_penalty}\right)$$

3. **Verdict Mapping & Caps**:
   The penalized score is scaled to $[0, 100]$ and bounded by strict verdict caps:
   - **`current`**: $\min(100, \text{round}(100 \cdot \text{penalized\_base}))$
   - **`partially_outdated`**: $\min(60, \text{round}(100 \cdot \text{penalized\_base}))$ (capped at 60)
   - **`outdated`**: $\min(25, \text{round}(100 \cdot \text{penalized\_base}))$ (capped at 25)
   - **`unverifiable`**: $\min(40, \text{round}(100 \cdot \text{penalized\_base}))$ (capped at 40, flagged as low confidence)
   - **`skipped`**: Fixed score of **100**, with explanation `"timeless/not time-sensitive"`.

---

## Overall Freshness Score

The answer-level `overall_freshness` score is a **volatility-weighted average** across all non-skipped claims:

$$\text{overall\_freshness} = \text{round}\left(\frac{\sum_{c \in \text{non-skipped}} w_c \cdot \text{freshness}(c)}{\sum_{c \in \text{non-skipped}} w_c}\right)$$

Where volatility weights are:
- `high`: $3.0$
- `medium`: $2.0$
- `low`: $1.0$

If all claims are skipped (e.g., timeless facts only), `overall_freshness` defaults to **100**.

---

## Configuration

All weights, half-lives, and caps are centralized in `backend/app/config.py` under `ScoringSettings` and can be adjusted dynamically for different domain requirements.

