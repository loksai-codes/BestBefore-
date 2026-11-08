'use client';

import React from 'react';
import { Check, Loader2 } from 'lucide-react';

interface ProgressStepperProps {
  currentStep: number;
  statusMessage?: string;
}

const STEPS = [
  { id: 0, title: 'Reading the label', desc: 'Parsing answer & claims' },
  { id: 1, title: 'Picking out the perishable claims', desc: 'Triaging volatility' },
  { id: 2, title: 'Checking the shelf (Tavily)', desc: 'Live web search & graph' },
  { id: 3, title: 'Judging freshness', desc: 'Evaluating live evidence' },
  { id: 4, title: 'Stamping dates', desc: 'Calculating best-before' },
  { id: 5, title: 'Corrected recipe', desc: 'Synthesizing citations' },
];

export default function ProgressStepper({ currentStep, statusMessage }: ProgressStepperProps) {
  return (
    <div className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-5 mb-6 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
            Shelf-Life Inspection
          </span>
          {statusMessage && (
            <span className="text-xs font-mono text-emerald-300/90 ml-2">
              &bull; {statusMessage}
            </span>
          )}
        </div>
        <span className="text-xs font-mono text-zinc-500">
          Step {Math.min(currentStep + 1, STEPS.length)} of {STEPS.length}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {STEPS.map((step) => {
          const isCompleted = currentStep > step.id;
          const isActive = currentStep === step.id;
          const isPending = currentStep < step.id;

          return (
            <div
              key={step.id}
              className={`p-3 rounded-lg border transition-all ${
                isActive
                  ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-200 shadow-sm shadow-emerald-500/10'
                  : isCompleted
                  ? 'bg-zinc-900/40 border-zinc-800 text-zinc-400'
                  : 'bg-zinc-950/30 border-zinc-850 text-zinc-600 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-medium ${
                    isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : isActive
                      ? 'bg-emerald-500 text-zinc-950 font-bold'
                      : 'bg-zinc-800 text-zinc-500'
                  }`}
                >
                  {isCompleted ? (
                    <Check className="w-3 h-3" />
                  ) : isActive ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    step.id + 1
                  )}
                </div>
                <div className="text-xs font-medium truncate">{step.title}</div>
              </div>
              <div className="text-[11px] text-zinc-500 truncate pl-7">
                {step.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
