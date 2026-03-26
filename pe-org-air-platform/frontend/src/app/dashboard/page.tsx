"use client";

import React, { useState, useEffect } from 'react';
import PortfolioDashboard, { PortfolioSummary, PortfolioCompany } from '@/components/PortfolioDashboard';

export default function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch Companies with scores via Aakash's PortfolioDataService
      const portfolioRes = await fetch('/api/v1/agent-ui/portfolio?fund_id=growth_fund_v');
      if (!portfolioRes.ok) throw new Error("Failed to fetch portfolio data");
      const companies: PortfolioCompany[] = await portfolioRes.json();

      // 2. Fetch Fund-level weighted metrics via Abhinav's FundAIRCalculator
      const fundRes = await fetch('/api/v1/agent-ui/fund-air?fund_id=growth_fund_v');
      if (!fundRes.ok) throw new Error("Failed to fetch fund metrics");
      const fundMetrics = await fundRes.json();

      setSummary({
        fund_id: fundMetrics.fund_id,
        fund_name: "Growth Equity Fund V",
        fund_ai_r: fundMetrics.fund_air,
        companies: companies.map(c => ({
            ...c,
            // Map EV from the backend's knowledge or default
            ev_mm: c.ticker === 'NVDA' ? 2200000 : c.ticker === 'JPM' ? 550000 : c.ticker === 'WMT' ? 480000 : 100000
        }))
      });
    } catch (err: any) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="min-h-screen bg-[#09090b] text-slate-300 p-8 pt-20">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">CS5 Portfolio Intelligence</h1>
            <p className="text-slate-500 text-sm">
                Connected to <strong>PortfolioDataService</strong>. 
                Metrics by <strong>FundAIRCalculator</strong>.
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <select className="bg-[#12151c] border border-slate-700 text-slate-300 text-sm rounded-lg block p-2.5">
              <option value="growth_fund_v">Growth Equity Fund V</option>
            </select>
            <button 
              onClick={fetchData}
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium px-4 py-2.5 rounded-lg transition"
            >
              {loading ? "Syncing..." : "Sync Live Data"}
            </button>
          </div>
        </div>

        {error ? (
          <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-xl text-red-400">
            <strong>Error:</strong> {error}
          </div>
        ) : summary ? (
          <PortfolioDashboard 
            summary={summary} 
            isLoading={loading}
          />
        ) : (
          <div className="h-64 flex items-center justify-center text-slate-500">Initializing...</div>
        )}
      </div>
    </div>
  );
}
