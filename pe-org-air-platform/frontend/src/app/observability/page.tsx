"use client";
import { useState, useEffect, useRef } from "react";
import { Activity, RefreshCw, Zap, Bot, UserCheck, Server, AlertTriangle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface LabeledCounts {
  success: number;
  error: number;
}

interface HITLEntry {
  reason: string;
  decision: string;
  count: number;
}

interface CSEntry {
  service: string;
  endpoint: string;
  success: number;
  error: number;
}

interface MetricsSnapshot {
  mcp_tool_calls: Record<string, LabeledCounts>;
  agent_invocations: Record<string, LabeledCounts>;
  hitl_approvals: Record<string, HITLEntry>;
  cs_client_calls: Record<string, CSEntry>;
}

function total(c: LabeledCounts) { return (c.success || 0) + (c.error || 0); }

function errorRate(c: LabeledCounts): string {
  const t = total(c);
  if (t === 0) return "0%";
  return `${((c.error / t) * 100).toFixed(1)}%`;
}

export default function ObservabilityPage() {
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/observability/metrics-snapshot`);
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      setMetrics(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(fetchMetrics, 15000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [autoRefresh]);

  const isEmpty = (obj: Record<string, unknown>) => Object.keys(obj).length === 0;

  const mcpTools = Object.entries(metrics?.mcp_tool_calls ?? {});
  const agents = Object.entries(metrics?.agent_invocations ?? {});
  const hitl = Object.values(metrics?.hitl_approvals ?? {});
  const csClients = Object.values(metrics?.cs_client_calls ?? {});

  const allEmpty = metrics && isEmpty(metrics.mcp_tool_calls) && isEmpty(metrics.agent_invocations) && isEmpty(metrics.hitl_approvals) && isEmpty(metrics.cs_client_calls);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-amber-600/20 rounded-xl flex items-center justify-center border border-amber-600/30">
            <Activity className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Observability</h1>
            <p className="text-slate-400 text-sm">Prometheus metrics: MCP tools, agents, HITL, CS integrations</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-slate-500">
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <label className="flex items-center gap-2 cursor-pointer">
            <div
              onClick={() => setAutoRefresh((v) => !v)}
              className={`w-10 h-5 rounded-full transition-colors relative ${autoRefresh ? "bg-amber-600" : "bg-slate-700"}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${autoRefresh ? "left-5" : "left-0.5"}`} />
            </div>
            <span className="text-sm text-slate-400">Auto-refresh (15s)</span>
          </label>
          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-4 mb-6 flex gap-3">
          <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
          <span className="text-sm text-red-300">{error}</span>
        </div>
      )}

      {loading && (
        <div className="text-center py-20 text-slate-500">
          <RefreshCw size={32} className="animate-spin mx-auto mb-4 text-slate-600" />
          <p>Loading metrics…</p>
        </div>
      )}

      {!loading && allEmpty && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
          <Activity size={40} className="text-slate-700 mx-auto mb-4" />
          <div className="text-slate-400 text-sm mb-2">No metrics recorded yet</div>
          <div className="text-slate-600 text-xs max-w-md mx-auto">
            Metrics are collected as tools are called, agents run, and HITL decisions are made.
            Run the Agentic Workflow or call MCP tools to generate data.
          </div>
        </div>
      )}

      {!loading && metrics && !allEmpty && (
        <div className="space-y-6">
          {/* MCP Tool Calls */}
          {mcpTools.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 p-5 border-b border-slate-800">
                <Zap size={16} className="text-violet-400" />
                <h2 className="text-sm font-semibold text-slate-300">MCP Tool Calls</h2>
                <span className="ml-auto text-xs text-slate-500">{mcpTools.length} tools instrumented</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-800 bg-slate-900/50">
                    <th className="py-2 px-5 text-left">Tool</th>
                    <th className="py-2 px-3 text-right">Total</th>
                    <th className="py-2 px-3 text-right">Success</th>
                    <th className="py-2 px-3 text-right">Error</th>
                    <th className="py-2 px-5 text-right">Error Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {mcpTools.map(([name, counts]) => (
                    <tr key={name} className="border-b border-slate-800/40 last:border-0 hover:bg-slate-800/20">
                      <td className="py-2.5 px-5 font-mono text-violet-300 text-xs">{name}</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">{total(counts)}</td>
                      <td className="py-2.5 px-3 text-right text-emerald-400">{counts.success}</td>
                      <td className="py-2.5 px-3 text-right text-red-400">{counts.error}</td>
                      <td className="py-2.5 px-5 text-right">
                        <span className={`text-xs font-medium ${counts.error > 0 ? "text-red-400" : "text-slate-500"}`}>
                          {errorRate(counts)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Agent Invocations */}
          {agents.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 p-5 border-b border-slate-800">
                <Bot size={16} className="text-blue-400" />
                <h2 className="text-sm font-semibold text-slate-300">Agent Invocations</h2>
                <span className="ml-auto text-xs text-slate-500">{agents.length} agents tracked</span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-800 bg-slate-900/50">
                    <th className="py-2 px-5 text-left">Agent</th>
                    <th className="py-2 px-3 text-right">Total</th>
                    <th className="py-2 px-3 text-right">Success</th>
                    <th className="py-2 px-3 text-right">Error</th>
                    <th className="py-2 px-5 text-right">Error Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map(([name, counts]) => (
                    <tr key={name} className="border-b border-slate-800/40 last:border-0 hover:bg-slate-800/20">
                      <td className="py-2.5 px-5 font-mono text-blue-300 text-xs">{name}</td>
                      <td className="py-2.5 px-3 text-right text-slate-300">{total(counts)}</td>
                      <td className="py-2.5 px-3 text-right text-emerald-400">{counts.success}</td>
                      <td className="py-2.5 px-3 text-right text-red-400">{counts.error}</td>
                      <td className="py-2.5 px-5 text-right">
                        <span className={`text-xs font-medium ${counts.error > 0 ? "text-red-400" : "text-slate-500"}`}>
                          {errorRate(counts)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* HITL Approvals */}
          {hitl.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 p-5 border-b border-slate-800">
                <UserCheck size={16} className="text-emerald-400" />
                <h2 className="text-sm font-semibold text-slate-300">HITL Approvals</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-800 bg-slate-900/50">
                    <th className="py-2 px-5 text-left">Reason</th>
                    <th className="py-2 px-3 text-left">Decision</th>
                    <th className="py-2 px-5 text-right">Count</th>
                  </tr>
                </thead>
                <tbody>
                  {hitl.map((entry, i) => (
                    <tr key={i} className="border-b border-slate-800/40 last:border-0 hover:bg-slate-800/20">
                      <td className="py-2.5 px-5 text-slate-300">{entry.reason}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          entry.decision === "approved" ? "bg-emerald-900/30 text-emerald-300" :
                          entry.decision === "rejected" ? "bg-red-900/30 text-red-300" :
                          "bg-slate-800 text-slate-400"
                        }`}>{entry.decision}</span>
                      </td>
                      <td className="py-2.5 px-5 text-right text-slate-300">{entry.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* CS Client Calls */}
          {csClients.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 p-5 border-b border-slate-800">
                <Server size={16} className="text-amber-400" />
                <h2 className="text-sm font-semibold text-slate-300">CS Integration Calls (CS1–CS4)</h2>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-slate-500 border-b border-slate-800 bg-slate-900/50">
                    <th className="py-2 px-5 text-left">Service</th>
                    <th className="py-2 px-3 text-left">Endpoint</th>
                    <th className="py-2 px-3 text-right">Success</th>
                    <th className="py-2 px-3 text-right">Error</th>
                    <th className="py-2 px-5 text-right">Error Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {csClients.map((entry, i) => (
                    <tr key={i} className="border-b border-slate-800/40 last:border-0 hover:bg-slate-800/20">
                      <td className="py-2.5 px-5">
                        <span className="px-2 py-0.5 bg-amber-900/20 text-amber-300 rounded text-xs font-mono">{entry.service}</span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 text-xs font-mono">{entry.endpoint}</td>
                      <td className="py-2.5 px-3 text-right text-emerald-400">{entry.success}</td>
                      <td className="py-2.5 px-3 text-right text-red-400">{entry.error}</td>
                      <td className="py-2.5 px-5 text-right">
                        <span className={`text-xs font-medium ${entry.error > 0 ? "text-red-400" : "text-slate-500"}`}>
                          {errorRate({ success: entry.success, error: entry.error })}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
