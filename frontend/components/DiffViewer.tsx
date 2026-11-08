'use client';

import React, { useState } from 'react';
import { Copy, Check, Sparkles, ArrowRight, ShieldCheck } from 'lucide-react';
import { ClaimResult } from '../types/api';

interface DiffViewerProps {
  originalAnswer: string;
  correctedAnswer: string;
  results: ClaimResult[];
}

export default function DiffViewer({
  originalAnswer,
  correctedAnswer,
  results,
}: DiffViewerProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(correctedAnswer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Extract changes summary from results
  const outdatedClaims = results.filter(
    (r) => r.verdict === 'outdated' || r.verdict === 'partially_outdated'
  );

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-5 shadow-sm backdrop-blur-sm animate-in fade-in duration-200">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-zinc-800 gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-zinc-100">
              Side-by-Side Verification Diff
            </h3>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Compare original stale claims with re-verified factual updates
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>Copied Answer!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy Corrected Answer</span>
            </>
          )}
        </button>
      </div>

      {/* Side-by-side comparison panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Original */}
        <div className="p-4 rounded-lg bg-zinc-950/80 border border-rose-500/20 text-xs">
          <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-zinc-800/80">
            <span className="font-semibold text-rose-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              Original Answer (Stale Claims Present)
            </span>
            <span className="text-[10px] font-mono text-zinc-500">Uncorrected</span>
          </div>
          <div className="text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">
            {originalAnswer}
          </div>
        </div>

        {/* Corrected */}
        <div className="p-4 rounded-lg bg-zinc-950/80 border border-emerald-500/20 text-xs">
          <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-zinc-800/80">
            <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Corrected Answer (Live Verified)
            </span>
            <span className="text-[10px] font-mono text-emerald-400 font-medium">
              Updated via Tavily
            </span>
          </div>
          <div className="text-zinc-100 leading-relaxed font-sans whitespace-pre-wrap">
            {correctedAnswer}
          </div>
        </div>
      </div>

      {/* Detected Changes List */}
      {outdatedClaims.length > 0 && (
        <div className="mt-5 pt-4 border-t border-zinc-800">
          <div className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-2.5">
            Key Factual Adjustments Made ({outdatedClaims.length})
          </div>

          <div className="space-y-2">
            {outdatedClaims.map((item) => (
              <div
                key={item.claim.id}
                className="p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
              >
                <div className="font-medium text-zinc-200">
                  <span className="text-zinc-400 font-mono text-[11px] mr-1">
                    [{item.claim.entity}]:
                  </span>
                  <span className="line-through text-rose-400/80 mr-2">
                    {item.claim.claimed_value}
                  </span>
                  <ArrowRight className="w-3 h-3 text-zinc-500 inline mr-2" />
                  <span className="text-emerald-400 font-semibold">
                    {item.current_value}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-zinc-500 shrink-0">
                  Freshness: {item.freshness_score}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

