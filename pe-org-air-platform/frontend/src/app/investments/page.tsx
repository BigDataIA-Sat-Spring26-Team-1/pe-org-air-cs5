"use client";
import { useState, useEffect } from "react";
import { TrendingUp, DollarSign, Award, AlertTriangle, RefreshCw, BarChart2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface InvestmentROI {
  company_id: string;
  company_name: string;
  entry_ev_mm: number;
  current_ev_mm: number;
  simple_roi_pct: number;
  annualized_roi_pct: number;
  moic: number;
  holding_period_years: number;
  org_air_delta: number;
  ai_attributed_value_pct: number;
  ai_attributed_value_mm: number;
  irr_estimate_pct: number;
  status: "active" | "realized" | "loss";
}

interface PortfolioROISummary {
  fund_id: string;
  total_invested_mm: number;
  total_current_value_mm: number;
  portfolio_moic: number;
  portfolio_roi_pct: number;
  weighted_avg_annualized_roi_pct: number;
  total_ai_attributed_value_mm: number;
  avg_ai_attribution_pct: number;
  investment_count: number;
  active_count: number;
  realized_count: number;
  loss_count: number;
  best_performer: InvestmentROI | null;
  worst_performer: InvestmentROI | null;
  avg_holding_period_years: number;
  avg_org_air_delta: number;
}

function fmt(v: number | undefined, decimals = 1): string {
  if (v === undefined || v === null) return "N/A";
  return v.toFixed(decimals);
}

function fmtMM(v: number | undefined): string {
  if (v === undefined || v === null) return "N/A";
  return `$${v.toFixed(1)}M`;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: "bg-emerald-900/30 text-emerald-300 border border-emerald-800/30",
    realized: "bg-blue-900/30 text-blue-300 border border-blue-800/30",
    loss: "bg-red-900/30 text-red-300 border border-red-800/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${styles[status] ?? "bg-slate-800 text-slate-400"}`}>
      {status}
    </span>
  );
}

export default function InvestmentsPage() {
  const [summary, setSummary] = useState<PortfolioROISummary | null>(null);
  const [investments, setInvestments] = useState<InvestmentROI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, listRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/investments/portfolio-roi`),
        fetch(`${API_BASE}/api/v1/investments/`),
      ]);

      if (!summaryRes.ok) throw new Error(`Portfolio ROI: ${summaryRes.statusText}`);
      if (!listRes.ok) throw new Error(`Investments list: ${listRes.statusText}`);

      const [summaryData, listData] = await Promise.all([summaryRes.json(), listRes.json()]);
      setSummary(summaryData);
      setInvestments(Array.isArray(listData) ? listData : []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const maxAI = Math.max(...investments.map((i) => i.ai_attributed_value_pct), 1);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-emerald-600/20 rounded-xl flex items-center justify-center border border-emerald-600/30">
            <TrendingUp className="w-6 h-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Investment ROI</h1>
            <p className="text-slate-400 text-sm">Portfolio returns with AI-readiness attribution</p>
          </div>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
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
          <p>Loading investment data…</p>
        </div>
      )}

      {!loading && summary && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-5 gap-4 mb-6">
            {[
              { label: "Total Invested", value: fmtMM(summary.total_invested_mm), icon: <DollarSign size={16} />, color: "text-slate-300" },
              { label: "Portfolio MOIC", value: `${fmt(summary.portfolio_moic, 2)}×`, icon: <TrendingUp size={16} />, color: "text-emerald-400" },
              { label: "Weighted Avg ROI", value: `${fmt(summary.weighted_avg_annualized_roi_pct)}%`, icon: <BarChart2 size={16} />, color: "text-blue-400" },
              { label: "AI-Attributed Value", value: fmtMM(summary.total_ai_attributed_value_mm), icon: <Award size={16} />, color: "text-violet-400" },
              { label: "Active Positions", value: `${summary.active_count} / ${summary.investment_count}`, icon: <TrendingUp size={16} />, color: "text-amber-400" },
            ].map(({ label, value, icon, color }) => (
              <div key={label} className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className={`flex items-center gap-1.5 text-xs text-slate-500 mb-2`}>
                  {icon}
                  {label}
                </div>
                <div className={`text-xl font-bold ${color}`}>{value}</div>
              </div>
            ))}
          </div>

          {/* Best / Worst */}
          {(summary.best_performer || summary.worst_performer) && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              {summary.best_performer && (
                <div className="bg-emerald-900/10 border border-emerald-800/30 rounded-xl p-5">
                  <div className="text-xs text-emerald-500 uppercase tracking-wider mb-2">Best Performer</div>
                  <div className="text-lg font-bold text-emerald-300">{summary.best_performer.company_name}</div>
                  <div className="flex gap-4 mt-2">
                    <div><div className="text-xs text-slate-500">ROI</div><div className="text-emerald-400 font-semibold">{fmt(summary.best_performer.simple_roi_pct)}%</div></div>
                    <div><div className="text-xs text-slate-500">MOIC</div><div className="text-emerald-400 font-semibold">{fmt(summary.best_performer.moic, 2)}×</div></div>
                    <div><div className="text-xs text-slate-500">AI Attr.</div><div className="text-emerald-400 font-semibold">{fmt(summary.best_performer.ai_attributed_value_pct)}%</div></div>
                  </div>
                </div>
              )}
              {summary.worst_performer && (
                <div className="bg-red-900/10 border border-red-800/30 rounded-xl p-5">
                  <div className="text-xs text-red-500 uppercase tracking-wider mb-2">Watch List</div>
                  <div className="text-lg font-bold text-red-300">{summary.worst_performer.company_name}</div>
                  <div className="flex gap-4 mt-2">
                    <div><div className="text-xs text-slate-500">ROI</div><div className="text-red-400 font-semibold">{fmt(summary.worst_performer.simple_roi_pct)}%</div></div>
                    <div><div className="text-xs text-slate-500">MOIC</div><div className="text-red-400 font-semibold">{fmt(summary.worst_performer.moic, 2)}×</div></div>
                    <div><div className="text-xs text-slate-500">Org-AI-R Δ</div><div className="text-red-400 font-semibold">{fmt(summary.worst_performer.org_air_delta)}</div></div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Per-Company Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-6">
            <div className="p-5 border-b border-slate-800">
              <h2 className="text-sm font-semibold text-slate-300">Portfolio Holdings</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500 border-b border-slate-800 bg-slate-900/50">
                    <th className="py-3 px-5">Company</th>
                    <th className="py-3 px-3">MOIC</th>
                    <th className="py-3 px-3">Simple ROI</th>
                    <th className="py-3 px-3">Ann. ROI</th>
                    <th className="py-3 px-3">IRR Est.</th>
                    <th className="py-3 px-3">AI Attr.</th>
                    <th className="py-3 px-3">Org-AI-R Δ</th>
                    <th className="py-3 px-3">Hold. Yrs</th>
                    <th className="py-3 px-5">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {investments.map((inv) => (
                    <tr key={inv.company_id} className="border-b border-slate-800/40 last:border-0 hover:bg-slate-800/20">
                      <td className="py-3 px-5">
                        <div className="font-semibold text-slate-200">{inv.company_name}</div>
                        <div className="text-xs text-slate-500">{fmtMM(inv.entry_ev_mm)} → {fmtMM(inv.current_ev_mm)}</div>
                      </td>
                      <td className={`py-3 px-3 font-bold ${inv.moic >= 1 ? "text-emerald-400" : "text-red-400"}`}>{fmt(inv.moic, 2)}×</td>
                      <td className={`py-3 px-3 ${inv.simple_roi_pct >= 0 ? "text-emerald-300" : "text-red-300"}`}>{fmt(inv.simple_roi_pct)}%</td>
                      <td className={`py-3 px-3 ${inv.annualized_roi_pct >= 0 ? "text-emerald-300" : "text-red-300"}`}>{fmt(inv.annualized_roi_pct)}%</td>
                      <td className="py-3 px-3 text-slate-300">{fmt(inv.irr_estimate_pct)}%</td>
                      <td className="py-3 px-3 text-violet-300">{fmt(inv.ai_attributed_value_pct)}%</td>
                      <td className={`py-3 px-3 ${inv.org_air_delta >= 0 ? "text-emerald-300" : "text-red-300"}`}>
                        {inv.org_air_delta >= 0 ? "+" : ""}{fmt(inv.org_air_delta)}
                      </td>
                      <td className="py-3 px-3 text-slate-400">{fmt(inv.holding_period_years, 1)}</td>
                      <td className="py-3 px-5"><StatusBadge status={inv.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* AI Attribution Bar Chart */}
          {investments.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-slate-300 mb-5">AI-Readiness Value Attribution</h2>
              <div className="space-y-3">
                {investments
                  .slice()
                  .sort((a, b) => b.ai_attributed_value_pct - a.ai_attributed_value_pct)
                  .map((inv) => (
                    <div key={inv.company_id} className="flex items-center gap-3">
                      <div className="w-28 text-sm text-slate-400 text-right shrink-0 truncate">{inv.company_name}</div>
                      <div className="flex-1 bg-slate-800 rounded-full h-4 overflow-hidden">
                        <div
                          className="h-full bg-violet-600 rounded-full transition-all duration-500"
                          style={{ width: `${(inv.ai_attributed_value_pct / maxAI) * 100}%` }}
                        />
                      </div>
                      <div className="w-16 text-sm text-violet-300 font-medium">{fmt(inv.ai_attributed_value_pct)}%</div>
                      <div className="w-20 text-xs text-slate-500">{fmtMM(inv.ai_attributed_value_mm)}</div>
                    </div>
                  ))}
              </div>
              <p className="text-xs text-slate-600 mt-4">
                AI attribution estimates the portion of value creation driven by Org-AI-R score improvement, using sector-specific coefficients (technology: 35%, financial: 30%, healthcare: 25%, manufacturing/retail: 20%, energy: 15%).
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
