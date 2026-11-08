'use client';

import React, { useMemo } from 'react';
import { ClaimResult } from '../types/api';
import { AlertCircle, Eye } from 'lucide-react';

interface HighlightedAnswerProps {
  answer: string;
  results: ClaimResult[];
  activeClaimId: string | null;
  onHoverClaim: (claimId: string | null) => void;
  onSelectClaim: (claimId: string) => void;
}

interface Segment {
  isClaim: boolean;
  text: string;
  claimResult?: ClaimResult;
}

export default function HighlightedAnswer({
  answer,
  results,
  activeClaimId,
  onHoverClaim,
  onSelectClaim,
}: HighlightedAnswerProps) {
  // Slices original answer into text segments and claim highlight segments
  const segments: Segment[] = useMemo(() => {
    if (!results || results.length === 0) {
      return [{ isClaim: false, text: answer }];
    }

    // Sort claims by start position
    const sorted = [...results].sort((a, b) => a.claim.span_start - b.claim.span_start);
    const segs: Segment[] = [];
    let cursor = 0;

    for (const r of sorted) {
      const start = Math.max(0, Math.min(r.claim.span_start, answer.length));
      const end = Math.max(start, Math.min(r.claim.span_end, answer.length));

      // Normal text before this claim
      if (start > cursor) {
        segs.push({
          isClaim: false,
          text: answer.slice(cursor, start),
        });
      }

      // Claim span
      segs.push({
        isClaim: true,
        text: answer.slice(start, end),
        claimResult: r,
      });

      cursor = end;
    }

    // Remaining text after last claim
    if (cursor < answer.length) {
      segs.push({
        isClaim: false,
        text: answer.slice(cursor),
      });
    }

    return segs;
  }, [answer, results]);

  const getVerdictStyle = (verdict: string, isActive: boolean) => {
    switch (verdict) {
      case 'current':
        return isActive
          ? 'bg-emerald-500/30 text-emerald-100 border-b-2 border-emerald-400 ring-2 ring-emerald-500/40'
          : 'bg-emerald-500/15 text-emerald-200 border-b-2 border-emerald-500/60 hover:bg-emerald-500/25';
      case 'partially_outdated':
        return isActive
          ? 'bg-amber-500/35 text-amber-100 border-b-2 border-amber-400 ring-2 ring-amber-500/40'
          : 'bg-amber-500/20 text-amber-200 border-b-2 border-amber-500/60 hover:bg-amber-500/30';
      case 'outdated':
        return isActive
          ? 'bg-rose-500/35 text-rose-100 border-b-2 border-rose-400 ring-2 ring-rose-500/40'
          : 'bg-rose-500/20 text-rose-200 border-b-2 border-rose-500/60 hover:bg-rose-500/30';
      default:
        return isActive
          ? 'bg-zinc-700/50 text-zinc-200 border-b-2 border-zinc-400 ring-2 ring-zinc-500/40'
          : 'bg-zinc-800/60 text-zinc-300 border-b-2 border-zinc-600 hover:bg-zinc-700/50';
    }
  };

  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 shadow-sm backdrop-blur-sm h-full flex flex-col">
      {/* Pane Header */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
            Original Answer & Claim Spans
          </h3>
        </div>
        <span className="text-[11px] text-zinc-500 font-mono">
          Hover span to inspect
        </span>
      </div>

      {/* Answer content with highlights */}
      <div className="flex-1 overflow-y-auto pr-1">
        <div className="text-sm leading-relaxed text-zinc-300 font-sans whitespace-pre-wrap select-text">
          {segments.map((seg, idx) => {
            if (!seg.isClaim || !seg.claimResult) {
              return <span key={idx}>{seg.text}</span>;
            }

            const r = seg.claimResult;
            const isActive = activeClaimId === r.claim.id;

            return (
              <mark
                key={idx}
                onMouseEnter={() => onHoverClaim(r.claim.id)}
                onMouseLeave={() => onHoverClaim(null)}
                onClick={() => onSelectClaim(r.claim.id)}
                className={`cursor-pointer px-1 py-0.5 rounded transition-all duration-150 inline font-normal ${getVerdictStyle(
                  r.verdict,
                  isActive
                )}`}
                title={`${r.verdict.toUpperCase()} (Freshness: ${r.freshness_score}%) - Click to focus`}
              >
                {seg.text}
              </mark>
            );
          })}
        </div>
      </div>

      {/* Expiry Stamp Legend */}
      <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center flex-wrap gap-3 text-[11px] text-zinc-400 font-mono">
        <span className="text-zinc-500 font-sans font-medium">Shelf-Life Stamps:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="font-semibold text-emerald-400">FRESH</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span className="font-semibold text-amber-400">PARTLY STALE</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          <span className="font-semibold text-rose-400">STALE</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-zinc-400" />
          <span className="font-semibold text-zinc-300">TIMELESS</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-zinc-600" />
          <span className="font-semibold text-zinc-400">UNVERIFIED</span>
        </div>
      </div>
    </div>
  );
}

