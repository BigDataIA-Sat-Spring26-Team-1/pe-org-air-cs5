"use client";
import { useState, useEffect } from "react";
import {
  GitBranch, Play, CheckCircle, Circle, Loader, AlertCircle,
  Download, ShieldAlert, UserCheck, XCircle, Clock,
} from "lucide-react";

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

interface HITLData {
  company_id: string;
  org_air?: number;
  approval_reason?: string;
  message?: string;
}

interface WorkflowResult {
  status?: "completed" | "pending_hitl" | "rejected";
  thread_id?: string;
  company_id: string;
  assessment_type?: string;
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
  hitl_data?: HITLData;
  value_creation_plan?: {
    gap_analysis?: {
      gaps?: Gap[];
      top_priority?: string;
      target_org_air?: number;
      gap_count?: number;
    };
  };
  messages?: { agent_name: string; content: string }[];
  error?: string;
}

type AgentStage = { id: string; label: string; description: string };

const STAGES: AgentStage[] = [
  { id: "sec",      label: "SEC Analyst",          description: "Fetching evidence signals from CS2" },
  { id: "scoring",  label: "Scoring Agent",         description: "Calculating Org-AI-R score via CS3" },
  { id: "evidence", label: "Evidence Agent",         description: "Generating dimension justifications" },
  { id: "value",    label: "Value Creation Agent",   description: "Running gap analysis & EBITDA projection" },
  { id: "hitl",     label: "HITL Review",            description: "Human-in-the-loop approval gate" },
  { id: "complete", label: "Complete",               description: "Workflow finished" },
];

function fmt(v: number | string | undefined, decimals = 1): string {
  if (v === undefined || v === null) return "N/A";
  const n = parseFloat(String(v));
  return isNaN(n) ? String(v) : n.toFixed(decimals);
}

export default function WorkflowPage() {
  const [companies, setCompanies]     = useState<Company[]>([]);
  const [selectedId, setSelectedId]   = useState("");
  const [assessmentType, setAssessmentType] = useState<"full" | "quick">("full");
  const [running, setRunning]         = useState(false);
  const [stageIndex, setStageIndex]   = useState(-1);
  const [result, setResult]           = useState<WorkflowResult | null>(null);
  const [error, setError]             = useState<string | null>(null);
  const [docStates, setDocStates]     = useState<Record<string, "idle"|"loading"|"done"|"error">>({});

  // HITL approval state
  const [hitlPending, setHitlPending] = useState(false);
  const [reviewedBy, setReviewedBy]   = useState("analyst");
  const [hitlNotes, setHitlNotes]     = useState("");
  const [hitlSubmitting, setHitlSubmitting] = useState(false);

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
    setHitlPending(false);
    setHitlNotes("");
    setStageIndex(0);

    // Simulate stage progression while waiting
    const stageTimer = setInterval(() => {
      setStageIndex((prev) => {
        const next = prev + 1;
        return next < STAGES.length - 1 ? next : prev;
      });
    }, 8000);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 300000); // 5 min
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

      const data: WorkflowResult = await res.json();

      if (data.status === "pending_hitl") {
        // Graph paused at HITL node — show the approval panel
        setStageIndex(4); // HITL stage index
        setHitlPending(true);
        setResult(data);
      } else {
        // Completed normally (no HITL triggered)
        setStageIndex(STAGES.length);
        setResult(data);
      }
    } catch (e: unknown) {
      clearInterval(stageTimer);
      setStageIndex(-1);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const submitHITLDecision = async (approved: boolean) => {
    if (!result?.thread_id) return;
    setHitlSubmitting(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/agent-ui/hitl/${result.thread_id}/decision`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ approved, reviewed_by: reviewedBy, notes: hitlNotes }),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
      }

      const finalResult: WorkflowResult = await res.json();
      setStageIndex(finalResult.status === "rejected" ? 4 : STAGES.length);
      setResult(finalResult);
      setHitlPending(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setHitlSubmitting(false);
    }
  };

  const downloadDoc = async (type: "ic-memo" | "lp-letter") => {
    if (!selectedId) return;
    setDocStates((s) => ({ ...s, [type]: "loading" }));
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
      setDocStates((s) => ({ ...s, [type]: "done" }));
      setTimeout(() => setDocStates((s) => ({ ...s, [type]: "idle" })), 3000);
    } catch {
      setDocStates((s) => ({ ...s, [type]: "error" }));
      setTimeout(() => setDocStates((s) => ({ ...s, [type]: "idle" })), 4000);
    }
  };

  const selectedCompany = companies.find((c) => c.company_id === selectedId);
  const scoring = result?.scoring_result;
  const gaps: Gap[] = result?.value_creation_plan?.gap_analysis?.gaps ?? [];
  const isCompleted = result?.status === "completed";
  const isRejected  = result?.status === "rejected";

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center border border-blue-600/30">
          <GitBranch className="w-6 h-6 text-blue-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Agentic Workflow</h1>
          <p className="text-slate-400 text-sm">LangGraph multi-agent due diligence pipeline with real HITL</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Controls + Pipeline */}
        <div className="col-span-1 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-300 mb-4">Configuration</h2>

            <label className="block text-xs text-slate-500 mb-1">Company</label>
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              disabled={running || hitlPending}
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
                  disabled={running || hitlPending}
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
                ? "Full: SEC → Scoring → Evidence → Value Creation → HITL (if triggered)."
                : "Quick: SEC → Scoring → Evidence → HITL (if triggered). No value creation."}
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
              disabled={running || hitlPending || !selectedId}
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
                const isDone   = stageIndex > idx;
                const isActive = stageIndex === idx && (running || hitlSubmitting || hitlPending);
                const isHitlWaiting = stage.id === "hitl" && hitlPending && !hitlSubmitting;
                return (
                  <div key={stage.id} className="flex items-start gap-3">
                    <div className="shrink-0 mt-0.5">
                      {isDone ? (
                        <CheckCircle size={16} className="text-emerald-400" />
                      ) : isHitlWaiting ? (
                        <Clock size={16} className="text-amber-400" />
                      ) : isActive ? (
                        <Loader size={16} className="text-blue-400 animate-spin" />
                      ) : (
                        <Circle size={16} className="text-slate-600" />
                      )}
                    </div>
                    <div>
                      <div className={`text-sm font-medium ${
                        isDone         ? "text-emerald-300"
                        : isHitlWaiting ? "text-amber-300"
                        : isActive      ? "text-blue-300"
                        : "text-slate-500"
                      }`}>
                        {stage.label}
                        {isHitlWaiting && <span className="ml-2 text-xs text-amber-400">· awaiting review</span>}
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

          {/* ── HITL Approval Panel ───────────────────────────────────────── */}
          {hitlPending && result?.hitl_data && (
            <div className="bg-amber-900/10 border border-amber-600/40 rounded-xl p-6 space-y-5">
              <div className="flex items-center gap-3">
                <ShieldAlert size={22} className="text-amber-400 shrink-0" />
                <div>
                  <h2 className="text-base font-bold text-amber-300">Human Review Required</h2>
                  <p className="text-xs text-amber-500 mt-0.5">
                    The LangGraph workflow has paused at the HITL gate and is waiting for your decision.
                  </p>
                </div>
              </div>

              {/* Trigger details */}
              <div className="bg-slate-900/60 border border-slate-700/50 rounded-lg p-4 space-y-2">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-slate-500">Company</div>
                    <div className="text-sm font-semibold text-slate-200">
                      {result.hitl_data.company_id}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Org-AI-R Score</div>
                    <div className="text-sm font-semibold text-blue-400">
                      {fmt(result.hitl_data.org_air ?? result.scoring_result?.org_air)}
                    </div>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">Approval Trigger</div>
                  <div className="text-sm text-amber-300 font-medium">
                    {result.hitl_data.approval_reason || result.approval_reason || "Score outside normal range"}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500 mb-1">HITL Message</div>
                  <div className="text-xs text-slate-400">{result.hitl_data.message}</div>
                </div>
              </div>

              {/* Reviewer input */}
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Reviewer Name</label>
                  <input
                    type="text"
                    value={reviewedBy}
                    onChange={(e) => setReviewedBy(e.target.value)}
                    disabled={hitlSubmitting}
                    placeholder="Your name or ID"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">Notes (optional)</label>
                  <textarea
                    value={hitlNotes}
                    onChange={(e) => setHitlNotes(e.target.value)}
                    disabled={hitlSubmitting}
                    rows={2}
                    placeholder="Add context for the approval/rejection…"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500 resize-none"
                  />
                </div>
              </div>

              {/* Decision buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => submitHITLDecision(true)}
                  disabled={hitlSubmitting || !reviewedBy.trim()}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition-colors"
                >
                  {hitlSubmitting ? <Loader size={16} className="animate-spin" /> : <UserCheck size={16} />}
                  {hitlSubmitting ? "Resuming workflow…" : "Approve & Continue"}
                </button>
                <button
                  onClick={() => submitHITLDecision(false)}
                  disabled={hitlSubmitting || !reviewedBy.trim()}
                  className="flex-1 flex items-center justify-center gap-2 py-3 bg-red-700 hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-sm font-semibold text-white transition-colors"
                >
                  {hitlSubmitting ? <Loader size={16} className="animate-spin" /> : <XCircle size={16} />}
                  Reject
                </button>
              </div>

              <p className="text-xs text-slate-600 text-center">
                The workflow graph is paused in LangGraph&#39;s MemorySaver. Your decision will resume it from exactly where it stopped.
              </p>
            </div>
          )}

          {/* ── Rejection Panel ───────────────────────────────────────────── */}
          {isRejected && (
            <div className="bg-red-900/10 border border-red-700/40 rounded-xl p-6 flex gap-4">
              <XCircle size={22} className="text-red-400 shrink-0 mt-0.5" />
              <div>
                <h2 className="text-base font-bold text-red-300 mb-1">Workflow Rejected</h2>
                <p className="text-sm text-red-400">
                  This due diligence assessment was rejected by{" "}
                  <span className="font-semibold">{result?.approved_by || "analyst"}</span>
                  {result?.approval_reason && ` — ${result.approval_reason}`}.
                  The workflow has been terminated and no further agents will run.
                </p>
              </div>
            </div>
          )}

          {!result && !error && !hitlPending && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
              <GitBranch size={40} className="text-slate-700 mx-auto mb-4" />
              <div className="text-slate-500 text-sm">Select a company and run the workflow to see results</div>
            </div>
          )}

          {/* Scores — show as soon as scoring is done (even during HITL wait) */}
          {scoring && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Org-AI-R Scores</h2>
              <div className="grid grid-cols-4 gap-3">
                {[
                  { label: "Org-AI-R",    value: scoring.org_air,     color: "text-blue-400"   },
                  { label: "Value Ready", value: scoring.vr_score,    color: "text-violet-400" },
                  { label: "Human Ready", value: scoring.hr_score,    color: "text-emerald-400"},
                  { label: "Synergy",     value: scoring.synergy_score, color: "text-amber-400"},
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-slate-800/50 rounded-lg p-3 text-center">
                    <div className={`text-2xl font-bold ${color}`}>{fmt(value)}</div>
                    <div className="text-xs text-slate-500 mt-1">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* HITL Status — only show after completion */}
          {isCompleted && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-3">HITL Governance</h2>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  !result.requires_approval
                    ? "bg-emerald-900/30 text-emerald-300 border border-emerald-800/30"
                    : result.approval_status === "approved"
                    ? "bg-blue-900/30 text-blue-300 border border-blue-800/30"
                    : result.approval_status === "rejected"
                    ? "bg-red-900/30 text-red-300 border border-red-800/30"
                    : "bg-amber-900/30 text-amber-300 border border-amber-800/30"
                }`}>
                  {!result.requires_approval
                    ? "No Approval Needed"
                    : result.approval_status === "approved"
                    ? "Approved by Human"
                    : result.approval_status === "rejected"
                    ? "Rejected by Human"
                    : result.approval_status || "Pending Review"}
                </span>
                {result.approved_by && (
                  <span className="text-xs text-slate-400">Reviewer: {result.approved_by}</span>
                )}
                {result.approval_reason && (
                  <span className="text-xs text-slate-500">· {result.approval_reason}</span>
                )}
              </div>
            </div>
          )}

          {/* Gap Analysis — only after completion */}
          {isCompleted && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-4">Gap Analysis by Dimension</h2>
              {gaps.length === 0 ? (
                <div className="text-center py-6">
                  <div className="text-emerald-400 text-sm font-medium mb-1">No gaps identified</div>
                  <div className="text-slate-500 text-xs">
                    Score ({fmt(result?.value_creation_plan?.gap_analysis?.target_org_air ?? scoring?.org_air)}) already meets target.
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
                              g.priority === "High"   ? "bg-red-900/30 text-red-300"    :
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
          )}

          {/* Document Downloads — only after completion */}
          {isCompleted && (
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
                        state === "done"    ? "bg-emerald-700 text-white" :
                        state === "error"   ? "bg-red-700 text-white" :
                        "bg-blue-600 hover:bg-blue-700 text-white"
                      }`}
                    >
                      <Download size={14} />
                      {state === "loading" ? "Generating…" : state === "done" ? "Downloaded!" : state === "error" ? "Failed" : label}
                    </button>
                  );
                })}
              </div>
              <p className="text-xs text-slate-500 mt-3">
                Documents reflect the workflow results above. Generation takes 15–30s.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
