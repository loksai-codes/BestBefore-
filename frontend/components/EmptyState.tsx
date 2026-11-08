'use client';

import React from 'react';
import { Sparkles, ArrowRight, Tag, Clock } from 'lucide-react';
import { SAMPLE_ANSWERS, SampleAnswer } from '../lib/mock';

interface EmptyStateProps {
  onSelectSample: (sample: SampleAnswer) => void;
}

export default function EmptyState({ onSelectSample }: EmptyStateProps) {
  return (
    <div className="bg-zinc-900/40 border border-zinc-800/80 border-dashed rounded-xl p-8 sm:p-12 text-center">
      <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
        <Tag className="w-6 h-6" />
      </div>

      <h3 className="text-lg font-semibold text-zinc-100 tracking-tight">
        Paste an AI answer and we&apos;ll check what&apos;s gone off.
      </h3>
      <p className="text-sm text-zinc-400 max-w-lg mx-auto mt-1.5 mb-8">
        AI claims have a shelf life. We stamp each time-sensitive claim with a freshness score and a best-before date, verified against live web evidence.
      </p>

      {/* 4 Quick Start Sample Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 max-w-4xl mx-auto text-left">
        {SAMPLE_ANSWERS.map((sample) => (
          <button
            key={sample.id}
            type="button"
            onClick={() => onSelectSample(sample)}
            className="group p-4 rounded-xl bg-zinc-900/80 hover:bg-zinc-850 border border-zinc-800 hover:border-emerald-500/40 transition-all flex flex-col justify-between"
          >
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold block mb-1">
                {sample.category}
              </span>
              <h4 className="text-xs font-semibold text-zinc-200 group-hover:text-zinc-100 transition-colors">
                {sample.title}
              </h4>
              <p className="text-[11px] text-zinc-500 mt-2 line-clamp-3">
                &ldquo;{sample.answer}&rdquo;
              </p>
            </div>

            <div className="mt-4 pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-400 group-hover:text-emerald-300">
              <span className="font-medium">Check shelf life</span>
              <ArrowRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
