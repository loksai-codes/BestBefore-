'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Play, Sparkles, Trash2, ChevronDown, Check } from 'lucide-react';
import { SAMPLE_ANSWERS, SampleAnswer } from '../lib/mock';

interface InputPanelProps {
  answer: string;
  onAnswerChange: (val: string) => void;
  onVerify: () => void;
  loading: boolean;
  rewriteEnabled: boolean;
  onToggleRewrite: (val: boolean) => void;
}

export default function InputPanel({
  answer,
  onAnswerChange,
  onVerify,
  loading,
  rewriteEnabled,
  onToggleRewrite,
}: InputPanelProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedSampleId, setSelectedSampleId] = useState<string>('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Keyboard shortcut: Cmd/Ctrl + Enter to trigger verification
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        if (!loading && answer.trim()) {
          e.preventDefault();
          onVerify();
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [loading, answer, onVerify]);

  const handleSelectSample = (sample: SampleAnswer) => {
    onAnswerChange(sample.answer);
    setSelectedSampleId(sample.id);
    setDropdownOpen(false);
  };

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;
  const charCount = answer.length;

  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-5 shadow-sm backdrop-blur-sm">
      {/* Top action row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium uppercase tracking-wider text-zinc-400">
            LLM Generated Answer
          </label>
          <span className="text-zinc-600">&bull;</span>
          <span className="text-[11px] text-zinc-500 font-mono">
            {wordCount} words / {charCount} chars
          </span>
        </div>

        {/* Controls: Samples dropdown & options */}
        <div className="flex items-center flex-wrap gap-2">
          {/* Sample answer selector dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/80 text-zinc-200 text-xs font-medium transition-all"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Load Sample Answer</span>
              <ChevronDown className={`w-3.5 h-3.5 text-zinc-400 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-1.5 w-72 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl shadow-black/50 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3 py-1 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider border-b border-zinc-800/80 mb-1">
                  Stale-Heavy Scenarios
                </div>
                {SAMPLE_ANSWERS.map((sample) => (
                  <button
                    key={sample.id}
                    type="button"
                    onClick={() => handleSelectSample(sample)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-zinc-800/70 text-zinc-300 hover:text-zinc-100 flex items-start justify-between gap-2 transition-colors"
                  >
                    <div>
                      <div className="font-medium text-zinc-200">{sample.title}</div>
                      <div className="text-[11px] text-zinc-500">{sample.category}</div>
                    </div>
                    {selectedSampleId === sample.id && (
                      <Check className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Clear button */}
          {answer && (
            <button
              type="button"
              onClick={() => {
                onAnswerChange('');
                setSelectedSampleId('');
              }}
              title="Clear input"
              className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Main Textarea */}
      <div className="relative">
        <textarea
          value={answer}
          onChange={(e) => onAnswerChange(e.target.value)}
          placeholder="Paste or type any AI-generated response containing pricing, SDK versions, regulations, executive changes, or time-sensitive factual assertions..."
          rows={5}
          className="w-full bg-zinc-950/80 border border-zinc-800 rounded-lg p-3.5 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-sans leading-relaxed resize-y transition-colors"
        />
      </div>

      {/* Bottom bar with options & verify button */}
      <div className="mt-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-zinc-800/60">
        {/* Rewrite Toggle */}
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={rewriteEnabled}
              onChange={(e) => onToggleRewrite(e.target.checked)}
              className="sr-only"
            />
            <div
              className={`w-8 h-4.5 rounded-full transition-colors relative p-0.5 ${
                rewriteEnabled ? 'bg-indigo-600' : 'bg-zinc-800'
              }`}
            >
              <div
                className={`w-3.5 h-3.5 rounded-full bg-white transition-transform ${
                  rewriteEnabled ? 'translate-x-3.5' : 'translate-x-0'
                }`}
              />
            </div>
            <span className="text-xs text-zinc-300 font-medium">
              Generate corrected answer diff
            </span>
          </label>
        </div>

        {/* Submit Button */}
        <div className="flex items-center gap-3">
          <span className="hidden md:inline-block text-[11px] text-zinc-500 font-mono">
            Press <kbd className="px-1 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-zinc-400 text-[10px]">⌘</kbd> + <kbd className="px-1 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-zinc-400 text-[10px]">Enter</kbd>
          </span>
          <button
            type="button"
            onClick={onVerify}
            disabled={loading || !answer.trim()}
            className="flex items-center justify-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white font-medium text-xs shadow-sm shadow-indigo-600/30 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Verifying Freshness...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Verify Freshness</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

