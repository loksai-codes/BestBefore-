'use client';

import React, { useState } from 'react';
import { ClaimResult, GatewayStats } from '../types/api';
import { isPastBestBefore } from '../lib/expiry';
import {
  Clock,
  Database,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  FileText,
  SplitSquareVertical,
  Activity,
  Copy,
  Check,
  Download,
  CalendarCheck,
} from 'lucide-react';

interface SummaryBarProps {
  overallFreshness: number;
  results: ClaimResult[];
  durationMs: number;
  graphAvailable: boolean;
  activeTab: 'claims' | 'diff' | 'gateway';
  onTabChange: (tab: 'claims' | 'diff' | 'gateway') => void;
  hasCorrectedAnswer: boolean;
  gatewayStats: GatewayStats;
  onCopyJson?: () => Promise<void>;
  onDownloadReport?: () => void;
}

export default function SummaryBar({
  overallFreshness,
  results,
  durationMs,
  graphAvailable,
  activeTab,
  onTabChange,
  hasCorrectedAnswer,
  gatewayStats,
  onCopyJson,
  onDownloadReport,
}: SummaryBarProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!onCopyJson) return;
    await onCopyJson();
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const freshCount = results.filter((r) => r.verdict === 'current').length;
  const partlyStaleCount = results.filter((r) => r.verdict === 'partially_outdated').length;
  const staleCount = results.filter((r) => r.verdict === 'outdated').length;
  const timelessCount = results.filter((r) => r.verdict === 'skipped').length;
  const unverifiedCount = results.filter((r) => r.verdict === 'unverifiable').length;

  // "X of Y claims are past their best-before date."
  const expiredCount = results.filter((r) => isPastBestBefore(r)).length;
  const totalClaims = results.length;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10';
    if (score >= 50) return 'text-amber-400 border-amber-500/40 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/40 bg-rose-500/10';
  };

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4 shadow-sm backdrop-blur-md mb-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Overall Freshness Score + Sentence + Expiry Stamps */}
        <div className="flex flex-wrap items-center gap-4 sm:gap-6">
          {/* Circular/Stamp Score Badge */}
          <div className="flex items-center gap-3">
            <div
              className={`w-14 h-14 rounded-xl border flex flex-col items-center justify-center p-1 font-mono ${getScoreColor(
                overallFreshness
              )}`}
            >
              <span className="text-xl font-bold leading-none">{overallFreshness}%</span>
              <span className="text-[9px] uppercase tracking-wider font-mono font-semibold opacity-80 mt-1">
                STAMP
              </span>
            </div>
            <div>
              <div className="text-xs font-semibold text-zinc-200 uppercase tracking-wide">
                Freshness
              </div>
              <div className="text-xs text-zinc-400 font-medium mt-0.5">
                <span className={expiredCount > 0 ? 'text-amber-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                  {expiredCount}
                </span>{' '}
                of {totalClaims} claims are past their best-before date.
              </div>
            </div>
          </div>

          <div className="h-8 w-px bg-zinc-800 hidden sm:block" />

          {/* Expiry Stamp Counters */}
          <div className="flex items-center flex-wrap gap-2 text-xs">
            {/* FRESH (current) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/30 border border-emerald-500/30 text-emerald-400 font-mono">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span className="font-bold">{freshCount}</span>
              <span className="text-[10px] uppercase tracking-wider font-semibold">FRESH</span>
            </div>

            {/* PARTLY STALE (partially_outdated) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-950/30 border border-amber-500/30 text-amber-400 font-mono">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span className="font-bold">{partlyStaleCount}</span>
              <span className="text-[10px] uppercase tracking-wider font-semibold">PARTLY STALE</span>
            </div>

            {/* STALE (outdated) */}
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-950/30 border border-rose-500/30 text-rose-400 font-mono">
              <XCircle className="w-3.5 h-3.5" />
              <span className="font-bold">{staleCount}</span>
              <span className="text-[10px] uppercase tracking-wider font-semibold">STALE</span>
            </div>

            {/* TIMELESS (skipped) */}
            {timelessCount > 0 && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-800/50 border border-zinc-700/60 text-zinc-400 font-mono">
                <CalendarCheck className="w-3.5 h-3.5" />
                <span className="font-bold">{timelessCount}</span>
                <span className="text-[10px] uppercase tracking-wider font-semibold">TIMELESS</span>
              </div>
            )}

            {/* UNVERIFIED (unverifiable) */}
            {unverifiedCount > 0 && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-800/40 border border-zinc-700/50 text-zinc-400 font-mono">
                <HelpCircle className="w-3.5 h-3.5" />
                <span className="font-bold">{unverifiedCount}</span>
                <span className="text-[10px] uppercase tracking-wider font-semibold">UNVERIFIED</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Meta stats & View Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between lg:justify-end gap-3 pt-3 lg:pt-0 border-t lg:border-t-0 border-zinc-800">
          {/* Metadata badges */}
          <div className="flex items-center gap-3 text-xs text-zinc-400 font-mono">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-zinc-500" />
              <span>{Math.round(durationMs)}ms</span>
            </span>
            <span className="text-zinc-700">&bull;</span>
            <span className="flex items-center gap-1 text-[11px]">
              <Database className="w-3.5 h-3.5 text-purple-400" />
              <span>{graphAvailable ? 'Graph Ready' : 'Graph Off'}</span>
            </span>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center p-1 rounded-lg bg-zinc-950 border border-zinc-800 text-xs">
            <button
              type="button"
              onClick={() => onTabChange('claims')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'claims'
                  ? 'bg-zinc-800 text-zinc-100 font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Stamped Claims</span>
            </button>

            {hasCorrectedAnswer && (
              <button
                type="button"
                onClick={() => onTabChange('diff')}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                  activeTab === 'diff'
                    ? 'bg-zinc-800 text-zinc-100 font-medium shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                <SplitSquareVertical className="w-3.5 h-3.5" />
                <span>Diff View</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => onTabChange('gateway')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
                activeTab === 'gateway'
                  ? 'bg-zinc-800 text-zinc-100 font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Gateway Stats</span>
            </button>
          </div>

          {/* Action buttons: Copy JSON & Download Report */}
          <div className="flex items-center gap-1.5">
            {onCopyJson && (
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-zinc-800/80 hover:bg-zinc-750 border border-zinc-700/80 text-zinc-300 hover:text-zinc-100 text-xs transition-colors"
                title="Copy verification response as JSON"
              >
                {copied ? (
                  <Check className="w-3 h-3 text-emerald-400" />
                ) : (
                  <Copy className="w-3 h-3 text-zinc-400" />
                )}
                <span>{copied ? 'Copied' : 'JSON'}</span>
              </button>
            )}

            {onDownloadReport && (
              <button
                type="button"
                onClick={onDownloadReport}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-zinc-800/80 hover:bg-zinc-750 border border-zinc-700/80 text-zinc-300 hover:text-zinc-100 text-xs transition-colors"
                title="Download BestBefore Markdown report"
              >
                <Download className="w-3 h-3 text-zinc-400" />
                <span>Report</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
