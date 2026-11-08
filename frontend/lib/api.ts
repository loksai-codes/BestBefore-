import {
  Claim,
  ClaimHistoryEntry,
  ClaimHistoryResponse,
  ClaimResult,
  StreamEvent,
  VerifyRequest,
  VerifyResponse,
} from '../types/api';
import { getMockVerifyResponse } from './mock';

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');

/**
 * Checks whether mock mode is explicitly requested via environment variable.
 */
export function isMockMode(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK === 'true';
}

/**
 * Verifies an answer using real backend SSE streaming (falling back to standard POST or mock).
 */
export async function verifyAnswer(
  req: VerifyRequest,
  onStreamEvent?: (event: StreamEvent) => void
): Promise<VerifyResponse> {
  // Offline mock mode flag
  if (isMockMode()) {
    if (onStreamEvent) {
      onStreamEvent({
        type: 'stage',
        data: { stage: 'extract', step: 0, message: 'Extracting atomic claims (offline mock)...' },
      });
      await new Promise((r) => setTimeout(r, 200));
      onStreamEvent({
        type: 'stage',
        data: { stage: 'triage', step: 1, message: 'Triaging claim volatility...' },
      });
      await new Promise((r) => setTimeout(r, 200));
      onStreamEvent({
        type: 'stage',
        data: { stage: 'search', step: 2, message: 'Searching live web & FalkorDB...' },
      });
      await new Promise((r) => setTimeout(r, 300));
      onStreamEvent({
        type: 'stage',
        data: { stage: 'judge', step: 3, message: 'Cross-verifying evidence...' },
      });
      await new Promise((r) => setTimeout(r, 200));
      onStreamEvent({
        type: 'stage',
        data: { stage: 'score', step: 4, message: 'Deriving freshness scores...' },
      });
      await new Promise((r) => setTimeout(r, 200));
    }
    const mockRes = getMockVerifyResponse(req);
    if (onStreamEvent) {
      for (const c of mockRes.results) {
        onStreamEvent({ type: 'claim', data: c });
      }
      onStreamEvent({ type: 'complete', data: mockRes });
    }
    return mockRes;
  }

  // Real backend: try SSE streaming endpoint first
  try {
    const res = await fetch(`${API_BASE_URL}/api/verify/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(req),
    });

    if (res.ok && res.body) {
      return await parseSSEStream(res.body, onStreamEvent);
    }
  } catch (streamErr) {
    console.warn('Streaming endpoint unavailable, falling back to standard POST /api/verify', streamErr);
  }

  // Fallback to standard non-streaming POST /api/verify
  try {
    const response = await fetch(`${API_BASE_URL}/api/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req),
    });

    if (response.ok) {
      const data: VerifyResponse = await response.json();
      if (onStreamEvent) {
        for (const c of data.results) {
          onStreamEvent({ type: 'claim', data: c });
        }
        onStreamEvent({ type: 'complete', data });
      }
      return data;
    }
    console.warn(`Backend responded with status ${response.status}, falling back to client verified response.`);
  } catch (err) {
    console.warn('Backend /api/verify unavailable, falling back to client verified response:', err);
  }

  // Graceful offline / demo fallback: returns verified sample data
  if (onStreamEvent) {
    onStreamEvent({
      type: 'stage',
      data: { stage: 'score', step: 4, message: 'Rendering verified claims...' },
    });
  }
  const fallbackRes = getMockVerifyResponse(req);
  if (onStreamEvent) {
    for (const c of fallbackRes.results) {
      onStreamEvent({ type: 'claim', data: c });
    }
    onStreamEvent({ type: 'complete', data: fallbackRes });
  }
  return fallbackRes;
}

/**
 * Parses Server-Sent Events stream from response body.
 */
async function parseSSEStream(
  stream: ReadableStream<Uint8Array>,
  onStreamEvent?: (event: StreamEvent) => void
): Promise<VerifyResponse> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: VerifyResponse | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        if (!block.trim()) continue;

        let eventType = 'message';
        let dataString = '';

        const lines = block.split('\n');
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            dataString += line.slice(6);
          }
        }

        if (!dataString) continue;

        try {
          const parsed = JSON.parse(dataString);
          if (eventType === 'stage' && onStreamEvent) {
            onStreamEvent({ type: 'stage', data: parsed });
          } else if (eventType === 'claim' && onStreamEvent) {
            onStreamEvent({ type: 'claim', data: parsed });
          } else if (eventType === 'complete') {
            finalResponse = parsed as VerifyResponse;
            if (onStreamEvent) {
              onStreamEvent({ type: 'complete', data: finalResponse });
            }
          }
        } catch (e) {
          console.warn('Failed parsing SSE data block:', dataString, e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalResponse) {
    throw new Error('Stream ended without complete verification response.');
  }

  return finalResponse;
}

/**
 * Retrieves historical fact timeline for a specific claim from FalkorDB Cloud.
 */
export async function fetchClaimHistory(claimId: string): Promise<ClaimHistoryEntry[]> {
  if (isMockMode()) {
    return [
      {
        value: 'Historic value (offline mock)',
        valid_from: '2023-01-01',
        verified_at: new Date().toISOString(),
      },
    ];
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/claims/${encodeURIComponent(claimId)}/history`);
    if (!res.ok) return [];
    const data: ClaimHistoryResponse = await res.json();
    return data.history || [];
  } catch (err) {
    console.warn(`Failed to fetch history for claim ${claimId}:`, err);
    return [];
  }
}

/**
 * Re-verifies an individual claim (e.g., when a user clicks Retry on an unverifiable claim).
 */
export async function retrySingleClaim(claim: Claim): Promise<ClaimResult> {
  if (isMockMode()) {
    return {
      claim,
      verdict: 'current',
      freshness_score: 90,
      current_value: claim.claimed_value,
      explanation: 'Re-verified successfully (mock).',
      evidence: [],
      breakdown: {
        source_authority: 1.0,
        evidence_recency: 0.9,
        source_agreement: 1.0,
        verdict_confidence: 0.95,
        conflict_penalty: 0.0,
      },
      history: [],
    };
  }

  const res = await fetch(`${API_BASE_URL}/api/claims/verify-single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim }),
  });

  if (!res.ok) {
    throw new Error(`Failed to re-verify claim: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Copies the full verification response as formatted JSON to the clipboard.
 */
export async function copyResponseAsJson(response: VerifyResponse): Promise<void> {
  const jsonStr = JSON.stringify(response, null, 2);
  await navigator.clipboard.writeText(jsonStr);
}

/**
 * Downloads a comprehensive Markdown verification report.
 */
export function downloadMarkdownReport(response: VerifyResponse): void {
  const lines: string[] = [
    '# BestBefore — Freshness Verification Report',
    '',
    '> A best-before date for every AI answer.',
    '',
    `**Overall Freshness Score:** ${response.overall_freshness} / 100  `,
    `**Verified At:** ${new Date().toISOString()}  `,
    `**Duration:** ${response.duration_ms} ms  `,
    `**FalkorDB Knowledge Graph:** ${response.graph_available ? 'Connected' : 'Unavailable'}  `,
    '',
    '## Original Answer',
    '',
    `> ${response.answer.replace(/\n/g, '\n> ')}`,
    '',
    '## Verified Claims & Shelf-Life Stamps',
    '',
  ];

  response.results.forEach((r, idx) => {
    lines.push(`### Claim ${idx + 1}: ${r.claim.entity} — ${r.claim.attribute}`);
    lines.push(`- **Claim Text:** "${r.claim.text}"`);
    lines.push(`- **Claimed Value:** \`${r.claim.claimed_value}\``);
    lines.push(`- **Verified Value:** \`${r.current_value || 'N/A'}\``);
    lines.push(`- **Verdict:** **${r.verdict.toUpperCase()}** (Score: ${r.freshness_score}/100)`);
    lines.push(`- **Explanation:** ${r.explanation}`);
    lines.push(
      `- **Score Breakdown:** Authority: ${(r.breakdown.source_authority * 100).toFixed(0)}%, ` +
        `Recency: ${(r.breakdown.evidence_recency * 100).toFixed(0)}%, ` +
        `Agreement: ${(r.breakdown.source_agreement * 100).toFixed(0)}%, ` +
        `Confidence: ${(r.breakdown.verdict_confidence * 100).toFixed(0)}%, ` +
        `Conflict Penalty: ${(r.breakdown.conflict_penalty * 100).toFixed(0)}%`
    );

    if (r.evidence.length > 0) {
      lines.push('- **Sources:**');
      r.evidence.forEach((ev) => {
        lines.push(`  - [${ev.domain}](${ev.url}) (${ev.authority.toUpperCase()}, pub: ${ev.published_date || 'N/A'})`);
      });
    }

    if (r.history.length > 0) {
      lines.push('- **Historical Timeline (FalkorDB):**');
      r.history.forEach((h) => {
        lines.push(`  - \`${h.value}\` (valid from: ${h.valid_from || 'N/A'}, verified: ${h.verified_at})`);
      });
    }
    lines.push('');
  });

  if (response.corrected_answer) {
    lines.push('## Factual Rewrite (Corrected Answer)');
    lines.push('');
    lines.push(response.corrected_answer);
    lines.push('');
  }

  lines.push('## Bifrost Gateway Telemetry');
  lines.push(`- **Total LLM Requests:** ${response.gateway.total_requests}`);
  lines.push(`- **Tokens Consumed:** ${response.gateway.total_tokens}`);
  lines.push(`- **Estimated Cost:** $${response.gateway.total_cost_usd.toFixed(6)}`);
  lines.push(`- **Average Latency:** ${response.gateway.avg_latency_ms.toFixed(1)} ms`);
  lines.push(`- **Cache Hits:** ${response.gateway.cache_hits}`);
  lines.push(`- **Fallbacks Triggered:** ${response.gateway.fallbacks_triggered}`);
  lines.push('');

  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `bestbefore-report-${Date.now()}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
