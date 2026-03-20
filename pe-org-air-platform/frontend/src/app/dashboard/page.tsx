"use client";

import React, { useState } from 'react';
import PortfolioDashboard, { PortfolioSummary } from '@/components/PortfolioDashboard';

const mockSummary: PortfolioSummary = {
    fund_id: "growth_fund_v",
    fund_name: "Growth Equity Fund V",
    fund_ai_r: 72.4, // EV-weighted Org-AI-R
    companies: [
        {
            company_id: "nvda-id",
            ticker: "NVDA",
            name: "NVIDIA Corporation",
            sector: "technology",
            org_air: 85.5,
            vr_score: 95.0,
            hr_score: 80.0,
            synergy_score: 1.25,
            entry_org_air: 60.0,
            delta_since_entry: 25.5,
            evidence_count: 342,
            ev_mm: 2200000
        },
        {
            company_id: "dg-id",
            ticker: "DG",
            name: "Dollar General",
            sector: "retail",
            org_air: 37.8,
            vr_score: 45.0,
            hr_score: 30.0,
            synergy_score: 1.05,
            entry_org_air: 35.0,
            delta_since_entry: 2.8,
            evidence_count: 21,
            ev_mm: 25000
        },
        {
            company_id: "jpm-id",
            ticker: "JPM",
            name: "JPMorgan Chase",
            sector: "financial_services",
            org_air: 71.2,
            vr_score: 75.0,
            hr_score: 65.0,
            synergy_score: 1.15,
            entry_org_air: 75.0,
            delta_since_entry: -3.8,
            evidence_count: 145,
            ev_mm: 450000
        },
        {
            company_id: "ge-id",
            ticker: "GE",
            name: "General Electric",
            sector: "manufacturing",
            org_air: 52.8,
            vr_score: 60.0,
            hr_score: 55.0,
            synergy_score: 1.08,
            entry_org_air: 40.0,
            delta_since_entry: 12.8,
            evidence_count: 85,
            ev_mm: 120000
        }
    ]
};

export default function DashboardPage() {
    const [data, setData] = useState(mockSummary);
    const [loading, setLoading] = useState(false);

    const handleRefresh = () => {
        setLoading(true);
        // Simulate network delay fetching from API or MCP
        setTimeout(() => setLoading(false), 1000);
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-slate-300 p-8 pt-20">
            <div className="max-w-7xl mx-auto">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-4">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">CS5 Portfolio Intelligence</h1>
                        <p className="text-slate-500 text-sm">Task 9.6 Placeholder. Connects to `PortfolioDataService` via CS1-CS4.</p>
                    </div>

                    <div className="flex items-center gap-3">
                        <select className="bg-[#12151c] border border-slate-700 text-slate-300 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block p-2.5">
                            <option value="growth_fund_v">Growth Equity Fund V</option>
                            <option value="buyout_fund_ii">Buyout Fund II</option>
                        </select>
                        <button
                            onClick={handleRefresh}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2.5 rounded-lg transition"
                        >
                            Sync Live Data
                        </button>
                    </div>
                </div>

                <PortfolioDashboard
                    summary={data}
                    isLoading={loading}
                />
            </div>
        </div>
    );
}
