'use client';

import React, { useState, useRef } from 'react';
import Header from '../components/Header';
import InputPanel from '../components/InputPanel';
import ProgressStepper from '../components/ProgressStepper';
import SummaryBar from '../components/SummaryBar';
import HighlightedAnswer from '../components/HighlightedAnswer';
import ClaimCard from '../components/ClaimCard';
import DiffViewer from '../components/DiffViewer';
import GatewayPanel from '../components/GatewayPanel';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import {
  verifyAnswer,
  retrySingleClaim,
  copyResponseAsJson,
  downloadMarkdownReport,
} from '../lib/api';
import { SAMPLE_ANSWERS, SampleAnswer } from '../lib/mock';
import { Claim, ClaimResult, StreamEvent, VerifyResponse } from '../types/api';

export default function Home() {
  const [answerInput, setAnswerInput] = useState<string>(SAMPLE_ANSWERS[0].answer);
  const [rewriteEnabled, setRewriteEnabled] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [result, setResult] = useState<VerifyResponse | null>(null);
  const [progressiveClaims, setProgressiveClaims] = useState<ClaimResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'claims' | 'diff' | 'gateway'>('claims');

  const claimsContainerRef = useRef<HTMLDivElement>(null);

  const handleVerify = async () => {
    if (!answerInput.trim()) return;

    setLoading(true);
    setError(null);
    setCurrentStep(0);
    setStatusMessage('Initiating verification pipeline...');
    setProgressiveClaims([]);

    try {
      const response = await verifyAnswer(
        {
          answer: answerInput,
          options: {
            rewrite: rewriteEnabled,
            max_claims: 10,
          },
        },
        (event: StreamEvent) => {
          if (event.type === 'stage') {
            setCurrentStep(event.data.step);
            if (event.data.message) {
              setStatusMessage(event.data.message);
            }
          } else if (event.type === 'claim') {
            setProgressiveClaims((prev) => {
              const exists = prev.some((c) => c.claim.id === event.data.claim.id);
              if (exists) {
                return prev.map((c) => (c.claim.id === event.data.claim.id ? event.data : c));
              }
              return [...prev, event.data];
            });
          } else if (event.type === 'complete') {
            setResult(event.data);
          }
        }
      );
      setResult(response);
      setActiveTab('claims');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error during verification';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleRetryClaim = async (claim: Claim) => {
    try {
      const updated = await retrySingleClaim(claim);
      setResult((prev) => {
        if (!prev) return null;
        const newResults = prev.results.map((r) => (r.claim.id === claim.id ? updated : r));
        const validScores = newResults
          .filter((r) => r.verdict !== 'skipped')
          .map((r) => r.freshness_score);
        const overall =
          validScores.length > 0
            ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
            : 100;
        return {
          ...prev,
          results: newResults,
          overall_freshness: overall,
        };
      });
    } catch (err) {
      console.error('Failed to retry claim verification:', err);
    }
  };

  const handleSelectSample = (sample: SampleAnswer) => {
    setAnswerInput(sample.answer);
    setResult(null);
    setProgressiveClaims([]);
    setError(null);
  };

  const handleSpanSelect = (claimId: string) => {
    setActiveClaimId(claimId);
    const cardEl = document.getElementById(`claim-card-${claimId}`);
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* 1. Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* 2. Input Panel */}
        <InputPanel
          answer={answerInput}
          onAnswerChange={(val) => {
            setAnswerInput(val);
          }}
          onVerify={handleVerify}
          loading={loading}
          rewriteEnabled={rewriteEnabled}
          onToggleRewrite={setRewriteEnabled}
        />

        {/* 9. Progress Stepper (during loading) */}
        {loading && (
          <div className="space-y-4">
            <ProgressStepper currentStep={currentStep} statusMessage={statusMessage} />
            {progressiveClaims.length > 0 && (
              <div className="space-y-3 p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-xl">
                <div className="flex items-center justify-between text-xs text-zinc-400">
                  <span className="font-semibold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                    Live Verified Claims Streaming In ({progressiveClaims.length})
                  </span>
                  <span className="font-mono text-[11px] text-zinc-500">
                    Tavily Web Search + FalkorDB Bi-Temporal Sync
                  </span>
                </div>
                <div className="space-y-3">
                  {progressiveClaims.map((res) => (
                    <ClaimCard
                      key={res.claim.id}
                      result={res}
                      isActive={activeClaimId === res.claim.id}
                      onHover={setActiveClaimId}
                      onRetryClaim={handleRetryClaim}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error Notification */}
        {error && <ErrorState message={error} onRetry={handleVerify} />}

        {/* Results View */}
        {result && !loading && (
          <div className="space-y-6">
            {/* 6. Summary Bar */}
            <SummaryBar
              overallFreshness={result.overall_freshness}
              results={result.results}
              durationMs={result.duration_ms}
              graphAvailable={result.graph_available}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              hasCorrectedAnswer={!!result.corrected_answer}
              gatewayStats={result.gateway}
              onCopyJson={async () => {
                if (result) await copyResponseAsJson(result);
              }}
              onDownloadReport={() => {
                if (result) downloadMarkdownReport(result);
              }}
            />

            {/* Tab 1: Claims & Evidence (Two columns) */}
            {activeTab === 'claims' && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left Column: Original answer with claim spans highlighted */}
                <div className="lg:col-span-5 lg:sticky lg:top-24 max-h-[calc(100vh-8rem)]">
                  <HighlightedAnswer
                    answer={result.answer}
                    results={result.results}
                    activeClaimId={activeClaimId}
                    onHoverClaim={setActiveClaimId}
                    onSelectClaim={handleSpanSelect}
                  />
                </div>

                {/* Right Column: List of Claim Cards */}
                <div
                  ref={claimsContainerRef}
                  className="lg:col-span-7 space-y-4 max-h-[calc(100vh-8rem)] overflow-y-auto pr-1"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-zinc-800 text-xs text-zinc-400">
                    <span className="font-semibold uppercase tracking-wider text-zinc-300">
                      Detected Claims & Evidence ({result.results.length})
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">
                      Hover card to highlight span
                    </span>
                  </div>

                  {result.results.map((res) => (
                    <ClaimCard
                      key={res.claim.id}
                      result={res}
                      isActive={activeClaimId === res.claim.id}
                      onHover={setActiveClaimId}
                      onRetryClaim={handleRetryClaim}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Tab 2: Corrected Answer Diff */}
            {activeTab === 'diff' && result.corrected_answer && (
              <DiffViewer
                originalAnswer={result.answer}
                correctedAnswer={result.corrected_answer}
                results={result.results}
              />
            )}

            {/* Tab 3: Bifrost Gateway Stats */}
            {activeTab === 'gateway' && <GatewayPanel stats={result.gateway} />}
          </div>
        )}

        {/* Empty State (when no verification performed and not loading) */}
        {!result && !loading && !error && (
          <EmptyState onSelectSample={handleSelectSample} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-zinc-500 font-mono">
          <div>
            Built for Geek Room Global AI Hackathon &bull; Tavily + Bifrost (Maxim AI) + FalkorDB Cloud
          </div>
          <div>
            Contract mirrored with <span className="text-zinc-400">/backend/app/schemas.py</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
