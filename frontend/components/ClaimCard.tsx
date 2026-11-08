'use client';

import React, { useState } from 'react';
import { Claim, ClaimHistoryEntry, ClaimResult, Evidence } from '../types/api';
import { fetchClaimHistory } from '../lib/api';
import { getClaimBestBefore } from '../lib/expiry';
import {
  ExternalLink,
  ChevronDown,
  BarChart2,
  History,
  Calendar,
  Globe,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ArrowRight,
  ShieldCheck,
  RotateCw,
  Loader2,
  Clock,
  CalendarCheck,
} from 'lucide-react';

interface ClaimCardProps {
  result: ClaimResult;
  isActive: boolean;
  onHover: (id: string | null) => void;
  onRetryClaim?: (claim: Claim) => Promise<void>;
}

export default function ClaimCard({
  result,
  isActive,
  onHover,
  onRetryClaim,
}: ClaimCardProps) {
  const [activeCardTab, setActiveCardTab] = useState<'details' | 'breakdown' | 'timeline'>('details');
  const [breakdownOpen, setBreakdownOpen] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [dynamicHistory, setDynamicHistory] = useState<ClaimHistoryEntry[] | null>(null);

  const { claim, verdict, freshness_score, current_value, explanation, evidence, breakdown, history } =
    result;

  const displayHistory = dynamicHistory || history || [];

  const handleToggleTimeline = async () => {
    const nextState = !timelineOpen;
    setTimelineOpen(nextState);
    if (nextState && displayHistory.length === 0) {
      setLoadingHistory(true);
      try {
        const hist = await fetchClaimHistory(claim.id);
        setDynamicHistory(hist);
      } finally {
        setLoadingHistory(false);
      }
    }
  };

  const handleRetry = async () => {
    if (!onRetryClaim || retrying) return;
    setRetrying(true);
    try {
      await onRetryClaim(claim);
    } finally {
      setRetrying(false);
    }
  };

  // BestBefore expiry stamp verdict configs
  const getVerdictConfig = (v: string) => {
    switch (v) {
      case 'current':
        return {
          label: 'FRESH',
          icon: CheckCircle2,
          color: 'text-emerald-400',
          badgeBg: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400',
          gaugeStroke: '#10b981',
        };
      case 'partially_outdated':
        return {
          label: 'PARTLY STALE',
          icon: AlertTriangle,
          color: 'text-amber-400',
          badgeBg: 'bg-amber-500/10 border-amber-500/40 text-amber-400',
          gaugeStroke: '#f59e0b',
        };
      case 'outdated':
        return {
          label: 'STALE',
          icon: XCircle,
          color: 'text-rose-400',
          badgeBg: 'bg-rose-500/10 border-rose-500/40 text-rose-400',
          gaugeStroke: '#ef4444',
        };
      case 'skipped':
        return {
          label: 'TIMELESS',
          icon: CalendarCheck,
          color: 'text-zinc-400',
          badgeBg: 'bg-zinc-800/60 border-zinc-700/60 text-zinc-300',
          gaugeStroke: '#a1a1aa',
        };
      default:
        return {
          label: 'UNVERIFIED',
          icon: HelpCircle,
          color: 'text-zinc-400',
          badgeBg: 'bg-zinc-800/40 border-zinc-700/50 text-zinc-400',
          gaugeStroke: '#71717a',
        };
    }
  };

  const vConfig = getVerdictConfig(verdict);
  const VerdictIcon = vConfig.icon;
  const bestBeforeInfo = getClaimBestBefore(claim, evidence, verdict);

  // Circular gauge calculations (radius 18)
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (freshness_score / 100) * circumference;

  const getAuthorityBadge = (auth: Evidence['authority']) => {
    switch (auth) {
      case 'official':
        return 'bg-blue-500/15 border-blue-500/30 text-blue-300';
      case 'reputable':
        return 'bg-purple-500/15 border-purple-500/30 text-purple-300';
      case 'community':
        return 'bg-amber-500/15 border-amber-500/30 text-amber-300';
      default:
        return 'bg-zinc-800 border-zinc-700 text-zinc-400';
    }
  };

  return (
    <div
      id={`claim-card-${claim.id}`}
      onMouseEnter={() => onHover(claim.id)}
      onMouseLeave={() => onHover(null)}
      className={`rounded-xl border transition-all duration-200 bg-zinc-900/80 p-5 backdrop-blur-sm ${
        isActive
          ? 'border-emerald-500/80 ring-2 ring-emerald-500/20 shadow-lg shadow-emerald-500/10'
          : 'border-zinc-800 hover:border-zinc-700/80'
      }`}
    >
      {/* Top Header: Circular gauge, Expiry stamp badge, Entity info */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          {/* Circular SVG Gauge */}
          <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
            <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 44 44">
              <circle
                cx="22"
                cy="22"
                r={radius}
                className="text-zinc-800"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="transparent"
              />
              <circle
                cx="22"
                cy="22"
                r={radius}
                stroke={vConfig.gaugeStroke}
                strokeWidth="3.5"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
                className="transition-all duration-500 ease-out"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-xs font-bold font-mono text-zinc-100">
                {freshness_score}
              </span>
            </div>
          </div>

          <div>
            <div className="flex items-center flex-wrap gap-1.5 mb-1">
              {/* Expiry Stamp Verdict Badge */}
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-mono text-[10.5px] uppercase font-bold tracking-wider border shadow-xs ${vConfig.badgeBg}`}
              >
                <VerdictIcon className="w-3 h-3" />
                <span>{vConfig.label}</span>
              </span>

              {/* Claim type */}
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-zinc-800 text-zinc-400 border border-zinc-700/60">
                {claim.claim_type}
              </span>

              {/* Volatility */}
              <span className="text-[10px] text-zinc-500">
                volatility: <span className="text-zinc-400">{claim.volatility}</span>
              </span>
            </div>

            <div className="text-xs font-medium text-zinc-300">
              <span className="text-zinc-100 font-semibold">{claim.entity}</span>
              {claim.attribute && (
                <span className="text-zinc-400"> &bull; {claim.attribute}</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Retry Button for unverifiable or manual recheck */}
          {onRetryClaim && (
            <button
              type="button"
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-zinc-700/80 transition-colors"
              title="Re-verify this claim against live sources"
            >
              {retrying ? (
                <Loader2 className="w-3 h-3 animate-spin text-emerald-400" />
              ) : (
                <RotateCw className="w-3 h-3 text-zinc-400" />
              )}
              <span>{retrying ? 'Retrying...' : 'Retry'}</span>
            </button>
          )}

          {/* Span character offset badge */}
          <span className="text-[10px] font-mono text-zinc-500 shrink-0 hidden sm:inline-block">
            [{claim.span_start}:{claim.span_end}]
          </span>
        </div>
      </div>

      {/* Best before Shelf Life Line */}
      <div
        className={`flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono my-2.5 transition-colors ${
          bestBeforeInfo.isPast
            ? 'bg-rose-950/20 border-rose-500/30 text-rose-300'
            : bestBeforeInfo.isTimeless
            ? 'bg-zinc-850 border-zinc-700 text-zinc-300'
            : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
        }`}
      >
        <div className="flex items-center gap-1.5 truncate">
          <Calendar className="w-3.5 h-3.5 shrink-0 opacity-80" />
          <span className="font-semibold truncate">{bestBeforeInfo.displayText}</span>
        </div>
        {bestBeforeInfo.statusNote && (
          <span className="shrink-0 text-[9.5px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40">
            {bestBeforeInfo.statusNote}
          </span>
        )}
      </div>

      {/* Claimed Text quote */}
      <blockquote className="my-2.5 pl-3 border-l-2 border-zinc-700 text-xs italic text-zinc-400 font-sans">
        &ldquo;{claim.text}&rdquo;
      </blockquote>

      {/* Value Comparison Box (Claimed vs Current) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 my-3 p-3 rounded-lg bg-zinc-950/70 border border-zinc-800/80 text-xs">
        <div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-zinc-500 block mb-0.5">
            Claimed Value in Answer
          </span>
          <span className="text-zinc-300 font-medium break-words">
            {claim.claimed_value || 'N/A'}
          </span>
        </div>

        <div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-emerald-400/90 flex items-center gap-1 mb-0.5">
            <ArrowRight className="w-3 h-3" />
            Current Verified Value
          </span>
          <span className="text-zinc-100 font-medium break-words">
            {current_value || claim.claimed_value}
          </span>
        </div>
      </div>

      {/* Explanation text */}
      <p className="text-xs leading-relaxed text-zinc-300 mb-3.5">
        {explanation}
      </p>

      {/* Source Chips */}
      {evidence && evidence.length > 0 && (
        <div className="mb-3.5">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 mb-1.5 flex items-center gap-1">
            <Globe className="w-3 h-3" />
            <span>Retrieved Sources ({evidence.length})</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {evidence.map((ev, idx) => (
              <a
                key={idx}
                href={ev.url}
                target="_blank"
                rel="noopener noreferrer"
                title={`${ev.title}\n${ev.snippet}`}
                className="group flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-950 border border-zinc-800 hover:border-zinc-700 text-zinc-300 hover:text-zinc-100 text-[11px] transition-all"
              >
                <span className="font-medium">{ev.domain}</span>
                <span
                  className={`text-[9px] px-1 py-0.2 rounded uppercase font-mono border ${getAuthorityBadge(
                    ev.authority
                  )}`}
                >
                  {ev.authority}
                </span>
                {ev.published_date && (
                  <span className="text-zinc-500 text-[10px]">
                    {ev.published_date}
                  </span>
                )}
                <ExternalLink className="w-3 h-3 text-zinc-500 group-hover:text-indigo-400 transition-colors" />
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Accordion Controls for Score Breakdown and Timeline */}
      <div className="border-t border-zinc-800/80 pt-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          {/* Score breakdown toggle */}
          <button
            type="button"
            onClick={() => setBreakdownOpen(!breakdownOpen)}
            className={`flex items-center gap-1 py-1 text-xs font-medium transition-colors ${
              breakdownOpen ? 'text-indigo-400' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <BarChart2 className="w-3.5 h-3.5" />
            <span>Score Breakdown</span>
            <ChevronDown
              className={`w-3 h-3 transition-transform ${breakdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Timeline toggle */}
          <button
            type="button"
            onClick={handleToggleTimeline}
            className={`flex items-center gap-1 py-1 text-xs font-medium transition-colors ${
              timelineOpen ? 'text-indigo-400' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>
              Timeline {displayHistory.length > 0 ? `(${displayHistory.length})` : ''}
            </span>
            {loadingHistory ? (
              <Loader2 className="w-3 h-3 animate-spin text-zinc-400" />
            ) : (
              <ChevronDown
                className={`w-3 h-3 transition-transform ${timelineOpen ? 'rotate-180' : ''}`}
              />
            )}
          </button>
        </div>
      </div>

      {/* Expandable Section 1: Score Breakdown horizontal bars */}
      {breakdownOpen && (
        <div className="mt-3 pt-3 border-t border-zinc-800/60 space-y-2.5 animate-in fade-in duration-150">
          <div className="text-[11px] font-medium text-zinc-400 mb-2">
            Freshness Scoring Weights & Penalties
          </div>

          {/* Component Bars */}
          <ScoreBar label="Source Authority" value={breakdown.source_authority} color="bg-blue-500" />
          <ScoreBar label="Evidence Recency" value={breakdown.evidence_recency} color="bg-emerald-500" />
          <ScoreBar label="Source Agreement" value={breakdown.source_agreement} color="bg-indigo-500" />
          <ScoreBar label="Verdict Confidence" value={breakdown.verdict_confidence} color="bg-purple-500" />
          <ScoreBar
            label="Conflict Penalty"
            value={breakdown.conflict_penalty}
            color="bg-rose-500"
            isPenalty
          />
        </div>
      )}

      {/* Expandable Section 2: Timeline history */}
      {timelineOpen && (
        <div className="mt-3 pt-3 border-t border-zinc-800/60 animate-in fade-in duration-150">
          <div className="text-[11px] font-medium text-zinc-400 mb-2.5">
            Historical Value Timeline (FalkorDB Temporal Graph)
          </div>

          {loadingHistory && (
            <div className="flex items-center gap-2 text-xs text-zinc-500 py-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
              <span>Querying FalkorDB Cloud...</span>
            </div>
          )}

          {!loadingHistory && displayHistory.length === 0 && (
            <div className="text-xs text-zinc-500 italic py-1">
              No historical predecessor facts found in knowledge graph.
            </div>
          )}

          {!loadingHistory && displayHistory.length > 0 && (
            <div className="relative pl-5 space-y-3 before:absolute before:left-2 before:top-1.5 before:bottom-1.5 before:w-0.5 before:bg-zinc-800">
              {displayHistory.map((item, idx) => (
                <div key={idx} className="relative group">
                  {/* Timeline node */}
                  <span
                    className={`absolute -left-5 top-1 w-2.5 h-2.5 rounded-full border-2 border-zinc-950 ${
                      idx === displayHistory.length - 1 ? 'bg-indigo-500 ring-2 ring-indigo-500/30' : 'bg-zinc-600'
                    }`}
                  />

                  <div className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-850 text-xs">
                    <div className="font-medium text-zinc-200">{item.value}</div>
                    <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-500 mt-1">
                      {item.valid_from && (
                        <span>Valid from: {item.valid_from}</span>
                      )}
                      <span>&bull;</span>
                      <span>Verified: {item.verified_at ? item.verified_at.slice(0, 10) : 'N/A'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreBar({
  label,
  value,
  color,
  isPenalty,
}: {
  label: string;
  value: number;
  color: string;
  isPenalty?: boolean;
}) {
  const percentage = Math.round(value * 100);

  return (
    <div>
      <div className="flex justify-between items-center text-[11px] mb-1">
        <span className="text-zinc-400">
          {label} {isPenalty && <span className="text-rose-400">(penalty)</span>}
        </span>
        <span className="font-mono text-zinc-300">{percentage}%</span>
      </div>
      <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
        />
      </div>
    </div>
  );
}

