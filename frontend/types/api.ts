export type ClaimType =
  | 'pricing'
  | 'api_version'
  | 'regulation'
  | 'leadership'
  | 'product_release'
  | 'other';

export type Volatility = 'high' | 'medium' | 'low';

export type Authority = 'official' | 'reputable' | 'community' | 'unknown';

export type Verdict =
  | 'current'
  | 'outdated'
  | 'partially_outdated'
  | 'unverifiable'
  | 'skipped';

export interface Claim {
  id: string;
  text: string;
  span_start: number;
  span_end: number; // char offsets in original answer
  entity: string;
  attribute: string;
  claimed_value: string;
  claim_type: ClaimType;
  volatility: Volatility;
  is_time_sensitive: boolean;
}

export interface Evidence {
  url: string;
  title: string;
  domain: string;
  snippet: string;
  published_date: string | null;
  authority: Authority;
  retrieved_at: string;
}

export interface ScoreBreakdown {
  source_authority: number; // 0..1
  evidence_recency: number; // 0..1
  source_agreement: number; // 0..1
  verdict_confidence: number; // 0..1
  conflict_penalty: number; // 0..1
}

export interface ClaimHistoryEntry {
  value: string;
  valid_from: string | null;
  verified_at: string;
}

export interface ClaimResult {
  claim: Claim;
  verdict: Verdict;
  freshness_score: number; // 0..100
  current_value: string | null;
  explanation: string;
  evidence: Evidence[];
  breakdown: ScoreBreakdown;
  history: ClaimHistoryEntry[];
}

export interface GatewayModelUsage {
  name: string;
  calls: number;
}

export interface GatewayStats {
  total_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  cache_hits: number;
  fallbacks_triggered: number;
  models_used: GatewayModelUsage[];
}

export interface VerifyOptions {
  rewrite?: boolean;
  max_claims?: number;
}

export interface VerifyRequest {
  answer: string;
  options?: VerifyOptions;
}

export interface VerifyResponse {
  answer: string;
  results: ClaimResult[];
  overall_freshness: number;
  corrected_answer: string | null;
  gateway: GatewayStats;
  graph_available: boolean;
  duration_ms: number;
  timings?: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  falkordb_reachable: boolean;
  bifrost_reachable: boolean;
  timestamp: string;
  details?: Record<string, string>;
}

export interface ClaimHistoryResponse {
  claim_id: string;
  history: ClaimHistoryEntry[];
}

export interface StageProgressEvent {
  stage: 'extract' | 'triage' | 'search' | 'judge' | 'score' | 'rewrite';
  step: number;
  message: string;
}

export type StreamEvent =
  | { type: 'stage'; data: StageProgressEvent }
  | { type: 'claim'; data: ClaimResult }
  | { type: 'complete'; data: VerifyResponse }
  | { type: 'error'; data: { message: string } };


