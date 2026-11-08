'use client';

import React from 'react';
import { AlertOctagon, RotateCcw } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-6 text-center my-6">
      <div className="w-10 h-10 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center mx-auto mb-3">
        <AlertOctagon className="w-5 h-5" />
      </div>
      <h3 className="text-sm font-semibold text-rose-300">
        Verification Request Failed
      </h3>
      <p className="text-xs text-rose-400/80 max-w-md mx-auto mt-1 mb-4">
        {message || 'An error occurred while communicating with the verification pipeline.'}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/40 text-rose-200 text-xs font-medium transition-colors"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Try Again</span>
      </button>
    </div>
  );
}

