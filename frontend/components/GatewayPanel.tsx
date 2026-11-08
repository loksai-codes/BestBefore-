'use client';

import React from 'react';
import { GatewayStats } from '../types/api';
import {
  Cpu,
  Layers,
  DollarSign,
  Gauge,
  Zap,
  ShieldAlert,
  Server,
  Activity,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface GatewayPanelProps {
  stats: GatewayStats;
}

export default function GatewayPanel({ stats }: GatewayPanelProps) {
  // Chart data for models used
  const chartData = stats.models_used.map((m) => ({
    name: m.name.length > 18 ? m.name.slice(0, 16) + '...' : m.name,
    fullName: m.name,
    calls: m.calls,
  }));

  const COLORS = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b'];

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-5 shadow-sm backdrop-blur-sm animate-in fade-in duration-200">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-5 border-b border-zinc-800 gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              Bifrost AI Gateway Telemetry
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                Active
              </span>
            </h3>
            <p className="text-xs text-zinc-400">
              High-performance inference metrics powered by Maxim AI Bifrost
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono">
          <span>Gateway: http://localhost:8080</span>
        </div>
      </div>

      {/* 6 Small Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {/* Total Requests */}
        <StatCard
          icon={Layers}
          label="Total Requests"
          value={stats.total_requests.toString()}
          sub="Gateway calls"
        />

        {/* Total Tokens */}
        <StatCard
          icon={Activity}
          label="Total Tokens"
          value={stats.total_tokens.toLocaleString()}
          sub="Prompt + Gen"
        />

        {/* Total Cost */}
        <StatCard
          icon={DollarSign}
          label="Total Cost"
          value={`$${stats.total_cost_usd.toFixed(5)}`}
          sub="USD computed"
        />

        {/* Latency */}
        <StatCard
          icon={Gauge}
          label="Avg Latency"
          value={`${stats.avg_latency_ms.toFixed(1)}ms`}
          sub="Time to response"
        />

        {/* Cache Hits */}
        <StatCard
          icon={Zap}
          label="Cache Hits"
          value={stats.cache_hits.toString()}
          sub="Semantic cache"
        />

        {/* Fallbacks */}
        <StatCard
          icon={ShieldAlert}
          label="Fallbacks"
          value={stats.fallbacks_triggered.toString()}
          sub="Model failovers"
        />
      </div>

      {/* Models Breakdown & Tiny Bar Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 pt-3 border-t border-zinc-800">
        {/* Models list */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3 flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5 text-zinc-500" />
            <span>Models Deployed via Bifrost</span>
          </div>

          <div className="space-y-2">
            {stats.models_used.map((model, i) => (
              <div
                key={model.name}
                className="flex items-center justify-between p-3 rounded-lg bg-zinc-950/60 border border-zinc-850 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: COLORS[i % COLORS.length] }}
                  />
                  <span className="font-mono text-zinc-200">{model.name}</span>
                </div>
                <span className="font-mono font-medium text-zinc-400">
                  {model.calls} {model.calls === 1 ? 'call' : 'calls'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Tiny Bar Chart */}
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-3 flex items-center justify-between">
            <span>Model Invocations Distribution</span>
            <span className="text-[10px] text-zinc-500 font-mono">Calls per Model</span>
          </div>

          <div className="h-44 w-full bg-zinc-950/60 border border-zinc-850 rounded-lg p-2 flex items-center justify-center">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <XAxis
                    dataKey="name"
                    stroke="#71717a"
                    fontSize={10}
                    tickLine={false}
                    axisLine={{ stroke: '#27272a' }}
                  />
                  <YAxis
                    stroke="#71717a"
                    fontSize={10}
                    allowDecimals={false}
                    tickLine={false}
                    axisLine={{ stroke: '#27272a' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#18181b',
                      borderColor: '#27272a',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: '#f4f4f5',
                    }}
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                  />
                  <Bar dataKey="calls" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={COLORS[index % COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs text-zinc-500">No chart data</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="p-3 rounded-lg bg-zinc-950/70 border border-zinc-800 flex flex-col justify-between">
      <div className="flex items-center justify-between text-zinc-500 mb-2">
        <span className="text-[11px] font-medium text-zinc-400 truncate">{label}</span>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div>
        <div className="text-base font-bold font-mono text-zinc-100">{value}</div>
        <div className="text-[10px] text-zinc-500 truncate">{sub}</div>
      </div>
    </div>
  );
}

