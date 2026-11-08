'use client';

import React from 'react';
import { Search, Cpu, Database, Sparkles } from 'lucide-react';

export default function Header() {
  return (
    <header className="border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {/* Brand: Logo glyph + Wordmark + Tagline */}
        <div className="flex items-center gap-3">
          {/* Minimal Calendar / Expiry Stamp Logo Glyph */}
          <div className="relative flex items-center justify-center w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-500/10 shrink-0">
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              {/* Calendar Tag outline */}
              <rect x="3" y="4" width="18" height="17" rx="3" />
              {/* Top bar header */}
              <line x1="3" y1="9" x2="21" y2="9" />
              {/* Binder rings */}
              <line x1="8" y1="2" x2="8" y2="5" />
              <line x1="16" y1="2" x2="16" y2="5" />
              {/* Clock checkmark */}
              <path d="M9 14.5l2 2 4-4" strokeWidth="2.2" />
            </svg>
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              {/* Wordmark: "Best" regular, "Before" bold */}
              <h1 className="text-lg tracking-tight flex items-baseline">
                <span className="font-normal text-zinc-200">Best</span>
                <span className="font-extrabold text-white">Before</span>
              </h1>
              <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-300 border border-zinc-700">
                v0.1.0
              </span>
            </div>
            {/* Tagline */}
            <p className="text-xs text-zinc-400 hidden sm:block">
              A best-before date for every AI answer.
            </p>
          </div>
        </div>

        {/* Integration Badges */}
        <div className="flex items-center flex-wrap gap-2 text-xs">
          {/* Hackathon Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[11px] font-medium text-zinc-300">Geek Room AI Hackathon</span>
          </div>

          {/* Tavily Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/90 border border-zinc-800 text-zinc-300 hover:border-zinc-700 transition-colors">
            <Search className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-[11px] font-medium">Tavily Search</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
          </div>

          {/* Bifrost by Maxim AI Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/90 border border-zinc-800 text-zinc-300 hover:border-zinc-700 transition-colors">
            <Cpu className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-[11px] font-medium">Bifrost Gateway</span>
            <span className="text-[10px] text-zinc-500 font-mono">Maxim AI</span>
          </div>

          {/* FalkorDB Cloud Badge */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900/90 border border-zinc-800 text-zinc-300 hover:border-zinc-700 transition-colors">
            <Database className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-[11px] font-medium">FalkorDB Cloud</span>
          </div>
        </div>
      </div>
    </header>
  );
}
