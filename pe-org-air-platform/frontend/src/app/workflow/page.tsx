"use client";
import { useState, useEffect } from "react";
import { GitBranch, Play, CheckCircle, Circle, Loader, AlertCircle, Download, ChevronRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface Company {
  company_id: string;
  ticker: string;
  name: string;
  sector: string;
  org_air: number;
}

interface Gap {
  dimension: string;
  current_score: number | string;
  target_score: number | string;
  gap: number | string;
  priority: string;
  initiatives?: string[];
}

interface WorkflowResult {
  company_id: string;
  assessment_type: string;
  scoring_result?: {
    org_air?: number;
    vr_score?: number;
    hr_score?: number;
    synergy_score?: number;
  };
  requires_approval?: boolean;
  approval_status?: string;
  approval_reason?: string;
  approved_by?: string;
  value_creation_plan?: {
    gap_analysis?: {
      gaps?: Gap[];
      top_priority?: string;
      target_org_air?: number;
      gap_count?: number;
    };
  };
  error?: string;
}

type AgentStage = {
  id: string;
  label: string;
  description: string;
};

const STAGES: AgentStage[] = [
  { id: "scoring", label: "Scoring Agent", description: "Calculating Org-AI-R score via CS3" },
  { id: "evidence", label: "Evidence Agent", description: "Fetching RAG justifications from CS4" },
  { id: "value", label: "Value Creation Agent", description: "Running gap analysis & EBITDA projection" },
  { id: "hitl", label: "HITL Check", description: "Human-in-the-loop approval review" },
  { id: "complete", label: "Complete", description: "Workflow finished" },
];

function fmt(v: number | string | undefined, decimals = 1): string {
  if (v === undefined || v === null) return "N/A";
  const n = parseFloat(String(v));
  return isNaN(n) ? String(v) : n.toFixed(decimals);
}

export default function WorkflowPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [assessmentType, setAssessmentType] = useState<"full" | "quick">("full");
  const [running, setRunning] = useState(false);
  const [stageIndex, setStageIndex] = useState(-1);
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [docStates, setDocStates] = useState<Record<string, "idle" | "loading" | "done" | "error">>({});

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/agent-ui/portfolio`)
      .then((r) => r.json())
      .then((data) => {
        const filtered = Array.isArray(data) ? data.filter((c: Company) => c.org_air > 0) : [];
        setCompanies(filtered);
        if (filtered.length > 0) setSelectedId(filtered[0].company_id);
      })
      .catch(() => {});
  }, []);

  const runWorkflow = async () => {
    if (!selectedId) return;
    setRunning(true);
    setResult(null);
    setError(null);
    setStageIndex(0);

    // Simulate stage progression while the real request runs
    const stageTimer = setInterval(() => {
      setStageIndex((prev) => {
        const next = prev + 1;
        return next < STAGES.length - 1 ? next : prev;
      });
    }, 8000);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 180000); // 3 min timeout
      const res = await fetch(`${API_BASE}/api/v1/agent-ui/trigger-due-diligence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_id: selectedId,
          assessment_type: assessmentType,
          requested_by: "analyst",
          target_org_air: 75.0,
        }),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      clearInterval(stageTimer);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }

      const data = await res.json();
      setStageIndex(STAGES.length); // > last index so Complete shows as done
      setResult(data);
    } catch (e: unknown) {
      clearInterval(stageTimer);
      setStageIndex(-1);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const downloadDoc = async (type: "ic-memo" | "lp-letter") => {
    if (!selectedId) return;
    const key = type;
    setDocStates((s) => ({ ...s, [key]: "loading" }));
    const endpoint = type === "ic-memo"
      ? `/api/v1/agent-ui/generate-ic-memo/${selectedId}`
      : `/api/v1/agent-ui/generate-lp-letter/${selectedId}`;
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method: "POST" });
      if (!res.ok) throw new Error(res.statusText);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = type === "ic-memo" ? `ic_memo_${selectedId}.docx` : `lp_letter_${selectedId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      setDocStates((s) => ({ ...s, [key]: "done" }));
      setTimeout(() => setDocStates((s) => ({ ...s, [key]: "idle" })), 3000);
    } catch {
      setDocStates((s) => ({ ...s, [key]: "error" }));
      setTimeout(() => setDocStates((s) => ({ ...s, [key]: "idle" })), 4000);
    }
  };

  const selectedCompany = companies.find((c) => c.company_id === selectedId);
  const scoring = result?.scoring_result;
  const gaps: Gap[] = result?.value_creation_plan?.gap_analysis?.gaps ?? [];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center border border-blue-600/30">
          <GitBranch className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Agentic Workflow</h1>
          <p className="text-slate-400 text-sm">LangGraph multi-agent due diligence pipeline</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Controls */}
        <div className="col-span-1 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Configuration</h2>

            <label className="block text-xs text-slate-500 mb-1">Company</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              disabled={running}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 mb-4 focus:outline-none focus:border-blue-500"
            >
              {companies.map((c) => (
                <option key={c.company_id} value={c.company_id}>
                  {c.ticker} — {c.name}
                </option>
              ))}
            </select>

            <label className="block text-xs text-slate-500 mb-1">Assessment Type</label>
            <div className="flex gap-2 mb-1">
              {(["full", "quick"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setAssessmentType(t)}
                  disabled={running}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                    assessmentType === t
                      ? "bg-blue-600 text-white"
                      : "bg-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-600 mb-4">
              {assessmentType === "full"
                ? "Full: Scoring → Evidence → Value Creation → HITL. Includes gap analysis & EBITDA projection."
                : "Quick: Scoring → Evidence → HITL. Skips value creation. Faster (~20–40s)."}
            </p>

            {selectedCompany && (
              <div className="bg-slate-800/50 rounded-lg p-3 mb-4">
                <div className="text-xs text-slate-500 mb-1">Current Org-AI-R</div>
                <div className="text-2xl font-bold text-blue-400">{fmt(selectedCompany.org_air)}</div>
                <div className="text-xs text-slate-500 mt-1">{selectedCompany.sector}</div>
              </div>
            )}

            <button
              onClick={runWorkflow}
              disabled={running || !selectedId}
              className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-semibold transition-colors"
            >
              {running ? <Loader size={16} className="animate-spin" /> : <Play size={16} />}
              {running ? "Running…" : "Run Due Diligence"}
            </button>
          </div>

          {/* Stage Progress */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Agent Pipeline</h2>
            <div className="space-y-3">
              {STAGES.map((stage, idx) => {
                const isDone = stageIndex > idx;
                const isActive = stageIndex === idx && running;
                const isPending = stageIndex < idx;
                return (
                  <div key={stage.id} className="flex items-start gap-3">
                    <div className="shrink-0 mt-0.5">
                      {isDone ? (
                        <CheckCircle size={16} className="text-emerald-400" />
                      ) : isActive ? (
                        <Loader size={16} className="text-blue-400 animate-spin" />
                      ) : (
                        <Circle size={16} className="text-slate-600" />
                      )}
                    </div>
                    <div>
                      <div className={`text-sm font-medium ${isDone ? "text-emerald-300" : isActive ? "text-blue-300" : "text-slate-500"}`}>
                        {stage.label}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">{stage.description}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right: Results */}
        <div className="col-span-2 space-y-4">
          {error && (
            <div className="bg-red-900/20 border border-red-800/50 rounded-xl p-5 flex gap-3">
              <AlertCircle size={18} className="text-red-400 shrink-0 mt-0.5" />
              <div>
                <div className="text-sm font-semibold text-red-300 mb-1">Workflow Failed</div>
                <div className="text-xs text-red-400">{error}</div>
              </div>
            </div>
          )}

          {!result && !error && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
              <GitBranch size={40} className="text-slate-700 mx-auto mb-4" />
              <div className="text-slate-500 text-sm">Select a company and run the workflow to see results</div>
            </div>
          )}

          {result && (
            <>
              {/* Scores */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">Org-AI-R Scores</h2>
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: "Org-AI-R", value: scoring?.org_air, color: "text-blue-400" },
                    { label: "Value Ready", value: scoring?.vr_score, color: "text-violet-400" },
                    { label: "Human Ready", value: scoring?.hr_score, color: "text-emerald-400" },
                    { label: "Synergy", value: scoring?.synergy_score, color: "text-amber-400" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-slate-800/50 rounded-lg p-3 text-center">
                      <div className={`text-2xl font-bold ${color}`}>{fmt(value)}</div>
                      <div className="text-xs text-slate-500 mt-1">{label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* HITL */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-300 mb-3">HITL Governance</h2>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    !result.requires_approval
                      ? "bg-emerald-900/30 text-emerald-300 border border-emerald-800/30"
                      : result.approval_status === "approved"
                      ? "bg-blue-900/30 text-blue-300 border border-blue-800/30"
                      : "bg-amber-900/30 text-amber-300 border border-amber-800/30"
                  }`}>
                    {!result.requires_approval ? "Standard Approval" : result.approval_status || "Pending Review"}
                  </span>
                  {result.approved_by && result.approved_by !== "N/A" && (
                    <span className="text-xs text-slate-400">Reviewed by: {result.approved_by}</span>
                  )}
                  {result.approval_reason && (
                    <span className="text-xs text-slate-500">· {result.approval_reason}</span>
                  )}
                </div>
              </div>

              {/* Gap Analysis */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">Gap Analysis by Dimension</h2>
                {gaps.length === 0 ? (
                  <div className="text-center py-6">
                    <div className="text-emerald-400 text-sm font-medium mb-1">No gaps identified</div>
                    <div className="text-slate-500 text-xs">
                      Org-AI-R score ({fmt(result?.value_creation_plan?.gap_analysis?.target_org_air ?? scoring?.org_air)}) already meets or exceeds the target.
                      All dimensions are above threshold.
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                          <th className="pb-2 pr-3">Dimension</th>
                          <th className="pb-2 pr-3">Current</th>
                          <th className="pb-2 pr-3">Target</th>
                          <th className="pb-2 pr-3">Gap</th>
                          <th className="pb-2">Priority</th>
                        </tr>
                      </thead>
                      <tbody>
                        {gaps.slice(0, 7).map((g) => (
                          <tr key={g.dimension} className="border-b border-slate-800/40 last:border-0">
                            <td className="py-2 pr-3 text-slate-200 capitalize">{g.dimension.replace(/_/g, " ")}</td>
                            <td className="py-2 pr-3 text-blue-400">{fmt(g.current_score)}</td>
                            <td className="py-2 pr-3 text-emerald-400">{fmt(g.target_score)}</td>
                            <td className="py-2 pr-3 text-amber-400 font-semibold">{fmt(g.gap)}</td>
                            <td className="py-2">
                              <span className={`px-2 py-0.5 rounded text-xs ${
                                g.priority === "High" ? "bg-red-900/30 text-red-300" :
                                g.priority === "Medium" ? "bg-amber-900/30 text-amber-300" :
                                "bg-slate-800 text-slate-400"
                              }`}>{g.priority}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Document Downloads */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h2 className="text-sm font-semibold text-slate-300 mb-4">Generated Documents</h2>
                <div className="flex gap-3">
                  {(["ic-memo", "lp-letter"] as const).map((type) => {
                    const state = docStates[type] || "idle";
                    const label = type === "ic-memo" ? "IC Memo" : "LP Letter";
                    return (
                      <button
                        key={type}
                        onClick={() => downloadDoc(type)}
                        disabled={state === "loading"}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                          state === "loading" ? "bg-slate-700 text-slate-400 cursor-wait" :
                          state === "done" ? "bg-emerald-700 text-white" :
                          state === "error" ? "bg-red-700 text-white" :
                          "bg-blue-600 hover:bg-blue-700 text-white"
                        }`}
                      >
                        <Download size={14} />
                        {state === "loading" ? "Generating…" : state === "done" ? "Downloaded!" : state === "error" ? "Failed" : label}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-slate-500 mt-3">Documents reflect the workflow results above. Generation takes 15-30s.</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
