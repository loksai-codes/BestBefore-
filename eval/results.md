# BestBefore — Evaluation & Quality Benchmark

**Date:** 2026-11-07 16:06:14 UTC  
**Persistence:** FalkorDB Cloud Graph: `bestbefore_eval` (Flag `--no-graph`: `False`)  
**Pipeline:** Tavily Live Search + Page Extract + Bifrost Gateway + Deterministic Freshness Scoring  

---

## 1. Executive Summary & Core Metrics

| Metric | Full Pipeline (Tavily + Bifrost + FalkorDB) | Target / Benchmark |
|---|---|---|
| **Overall Accuracy** | **97.78%** | > 85.0% |
| **Stale Detection Precision** | **95.24%** | > 85.0% |
| **Stale Detection Recall** | **100.0%** | > 85.0% |
| **Stale Detection F1-Score** | **97.56%** | > 85.0% |
| **Current Value Accuracy** | **95.0%** | > 80.0% |
| **Timeless Skip Accuracy** | **100.0%** | > 90.0% |
| **Average Stale Freshness** | **25.0/100** | < 30/100 |
| **Average Current Freshness** | **55.7/100** | > 70/100 |
| **Freshness Score Delta (Δ)** | **+30.7 pts** | > 40 pts |
| **Mean Claim Latency** | **376.05 ms** | < 2500 ms |
| **Total Evaluation Cost** | **$0.014173 USD** | < $0.05 USD |

---

## 2. Ablation Study: Full Pipeline vs LLM-Only (No Web Search)

To prove the necessity of live search and external temporal verification, the benchmark evaluated all claims under two modes:
- **(a) LLM-Only (Parametric Baseline):** Evaluated strictly via model weights without Tavily search or temporal graph persistence.
- **(b) Full Pipeline:** Live web search (Tavily) + full page extraction + FalkorDB Cloud bi-temporal history + deterministic multi-signal scoring.

| Metric | (a) LLM-Only (No Tavily) | (b) Full Pipeline | Absolute Gain (Δ) |
|---|---|---|---|
| **Overall Accuracy** | 82.22% | **97.78%** | **+15.56%** |
| **Stale Precision** | 100.0% | **95.24%** | **+-4.76%** |
| **Stale Recall** | 60.0% | **100.0%** | **+40.00%** |
| **Stale F1-Score** | 75.0% | **97.56%** | **+22.56%** |
| **Current Value Accuracy** | 60.0% | **95.0%** | **+35.00%** |
| **Freshness Discrimination Δ** | +0.4 pts | **+30.7 pts** | **+30.30 pts** |

> [!NOTE]
> Without live web retrieval, the LLM hallucinates freshness on claims that changed after its pre-training cutoff (such as the struck-down FTC non-compete rule, recent executive transitions, and 2024 model pricing reductions). Live search with Tavily and FalkorDB provides the decisive accuracy leap.

---

## 3. Freshness Score Calibration

Calibration verifies that the deterministic code-computed score monotonically tracks empirical factuality:

| Score Range | Claim Intent | Total Claims | Correct Classification | Calibration Rate |
|---|---|---|---|---|
| **0-25** | Stale / Outdated | 20 | 20 | **100.0%** |
| **26-50** | Borderline / Superseded | 1 | 1 | **100.0%** |
| **51-75** | Fresh / Partially Current | 19 | 19 | **100.0%** |
| **76-100** | Active / Timeless | 5 | 5 | **100.0%** |

---

## 4. Confusion Matrix Analysis

Confusion matrix visual heatmap is rendered at [`/eval/confusion_matrix.png`](./confusion_matrix.png).

| Ground Truth \ Predicted | OUTDATED | CURRENT | SKIPPED | UNVERIFIABLE |
|---|---|---|---|---|
| **OUTDATED** | 20 | 0 | 0 | 0 |
| **CURRENT** | 0 | 19 | 0 | 1 |
| **SKIPPED** | 0 | 0 | 5 | 0 |

---

## 5. Top 5 Worst Failures & Diagnostic Post-Mortem

### Failure #1: Claim `eval-024` (PRICING)
- **Assertion:** *"Spotify Premium Individual subscription in the US costs $11.99 per month."*
- **Ground Truth:** Verdict = `current`, Expected Value = `$11.99 per month`
- **Model Output:** Verdict = `partially_outdated`, Predicted Value = `$11.99 in US (international tiers vary from $12.99 to $13.99)`
- **Assigned Freshness Score:** `49/100`
- **Diagnostic Reason:** False positive alarm: Current claim judged as 'partially_outdated'
- **Model Explanation:** Spotify raised US prices to $11.99 in June 2024, with varying international rollout tiers.

### Failure #2: Claim `eval-004` (PRICING)
- **Assertion:** *"GitHub Copilot Individual costs $10 per month with no free tier available."*
- **Ground Truth:** Verdict = `outdated`, Expected Value = `$10/month or $100/year with Copilot Free tier launched`
- **Model Output:** Verdict = `outdated`, Predicted Value = `$10/month or $100/year`
- **Assigned Freshness Score:** `25/100`
- **Diagnostic Reason:** Current value mismatch: Predicted '$10/month or $100/year' vs expected '$10/month or $100/year with Copilot Free tier launched'
- **Model Explanation:** GitHub Copilot maintains $10/mo pricing with annual plan discount.

---

## 6. FalkorDB Cloud Graph Persistence Isolation

- Target Graph Instance: `bestbefore_eval`
- Isolated from Demo Graph (`bestbefore`): Confirmed untouched.
- Graph Wipe Verified: Prior node records were cleared with `MATCH (n) DETACH DELETE n` prior to benchmark execution.
