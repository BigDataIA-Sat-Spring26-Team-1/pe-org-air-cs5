"use client";

import React from 'react';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ZAxis,
    Cell
} from 'recharts';

export interface PortfolioCompany {
    company_id: string;
    ticker: string;
    name: string;
    sector: string;
    org_air: number;
    vr_score: number;
    hr_score: number;
    synergy_score: number;
    entry_org_air: number;
    delta_since_entry: number;
    evidence_count: number;
    ev_mm: number; // Enterprise Value in Millions
}

export interface PortfolioSummary {
    fund_id: string;
    fund_name: string;
    fund_ai_r: number;
    companies: PortfolioCompany[];
}

interface PortfolioDashboardProps {
    summary: PortfolioSummary;
    isLoading?: boolean;
}

export default function PortfolioDashboard({ summary, isLoading = false }: PortfolioDashboardProps) {
    if (isLoading) {
        return (
            <div className="animate-pulse space-y-6">
                <div className="h-32 bg-slate-800 rounded-xl"></div>
                <div className="h-96 bg-slate-800 rounded-xl"></div>
                <div className="h-64 bg-slate-800 rounded-xl"></div>
            </div>
        );
    }

    // Format the data for the scatter plot
    const scatterData = summary.companies.map(c => ({
        name: c.ticker,
        x: c.hr_score,     // Hazard Risk (H^R) on X
        y: c.vr_score,     // Value Creation (V^R) on Y
        z: c.ev_mm,        // Bubble size by EV
        score: c.org_air   // Determines base color intensity
    }));

    const getDeltaColor = (delta: number) => {
        if (delta > 5) return "text-emerald-400";
        if (delta > 0) return "text-green-400";
        if (delta < -5) return "text-red-400";
        if (delta < 0) return "text-orange-400";
        return "text-slate-400";
    };

    const getScoreBadge = (score: number) => {
        if (score >= 80) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
        if (score >= 60) return "bg-green-500/10 text-green-400 border-green-500/20";
        if (score >= 40) return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
        if (score >= 20) return "bg-orange-500/10 text-orange-400 border-orange-500/20";
        return "bg-red-500/10 text-red-400 border-red-500/20";
    };

    return (
        <div className="flex flex-col gap-6">

            {/* Top Value Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-[#12151c] border border-slate-800 p-6 rounded-xl shadow-lg">
                    <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-2">Fund-AI-R Score</h3>
                    <div className="text-4xl font-bold text-white flex items-end gap-3">
                        {summary.fund_ai_r.toFixed(1)}
                        <span className="text-sm font-medium text-emerald-400 mb-1">+2.4 pts QoQ</span>
                    </div>
                    <p className="text-slate-500 mt-2 text-sm">EV-weighted average of the portfolio.</p>
                </div>

                <div className="bg-[#12151c] border border-slate-800 p-6 rounded-xl shadow-lg">
                    <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-2">Portfolio Coverage</h3>
                    <div className="text-4xl font-bold text-white">
                        {summary.companies.length}
                        <span className="text-xl text-slate-500 ml-2">Active</span>
                    </div>
                    <p className="text-slate-500 mt-2 text-sm">Companies fully mapped via MCP integration.</p>
                </div>

                <div className="bg-[#12151c] border border-slate-800 p-6 rounded-xl shadow-lg">
                    <h3 className="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-2">Total Evidence Points</h3>
                    <div className="text-4xl font-bold text-white">
                        {summary.companies.reduce((acc, c) => acc + c.evidence_count, 0).toLocaleString()}
                    </div>
                    <p className="text-slate-500 mt-2 text-sm">Granular signals processed across the fund.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Scatter Plot */}
                <div className="bg-[#12151c] border border-slate-800 rounded-xl shadow-lg p-6">
                    <h3 className="text-lg font-bold text-slate-100 mb-6 flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                        V^R vs H^R Quadrant Mapping
                    </h3>
                    <div className="h-[400px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 10 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                                <XAxis
                                    type="number"
                                    dataKey="x"
                                    name="Hazard Risk (H^R)"
                                    domain={[0, 100]}
                                    tick={{ fill: '#a0aec0' }}
                                    label={{ value: "Hazard Risk (H^R)", position: 'bottom', fill: '#cbd5e1' }}
                                />
                                <YAxis
                                    type="number"
                                    dataKey="y"
                                    name="Value Creation (V^R)"
                                    domain={[0, 100]}
                                    tick={{ fill: '#a0aec0' }}
                                    label={{ value: "Value Creation (V^R)", angle: -90, position: 'left', fill: '#cbd5e1' }}
                                />
                                <ZAxis type="number" dataKey="z" range={[60, 400]} />
                                <Tooltip
                                    cursor={{ strokeDasharray: '3 3' }}
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            const data = payload[0].payload;
                                            return (
                                                <div className="bg-[#1e293b] border border-slate-700 p-3 rounded-lg shadow-xl">
                                                    <p className="font-bold text-white mb-1">{data.name}</p>
                                                    <p className="text-sm text-slate-300">V^R Score: {data.y.toFixed(1)}</p>
                                                    <p className="text-sm text-slate-300">H^R Score: {data.x.toFixed(1)}</p>
                                                    <p className="text-sm text-blue-300 mt-1">Org-AI-R: {data.score.toFixed(1)}</p>
                                                    <p className="text-xs text-slate-500 mt-1">EV: ${data.z}M</p>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                <Scatter data={scatterData}>
                                    {scatterData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.score > 70 ? '#10b981' : entry.score > 40 ? '#f59e0b' : '#ef4444'} opacity={0.8} />
                                    ))}
                                </Scatter>
                            </ScatterChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Company Roster Table */}
                <div className="bg-[#12151c] border border-slate-800 rounded-xl shadow-lg p-6 overflow-hidden flex flex-col">
                    <h3 className="text-lg font-bold text-slate-100 mb-6 flex items-center gap-2">
                        <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18M4 6h16a1 1 0 011 1v10a1 1 0 01-1 1H4a1 1 0 01-1-1V7a1 1 0 011-1z" />
                        </svg>
                        Portfolio Holdings
                    </h3>
                    <div className="flex-1 overflow-auto -mx-6 px-6">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
                                    <th className="pb-3 font-medium">Company</th>
                                    <th className="pb-3 font-medium">Org-AI-R</th>
                                    <th className="pb-3 font-medium hidden sm:table-cell">Delta</th>
                                    <th className="pb-3 font-medium text-right">Synergy</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/50">
                                {summary.companies.sort((a, b) => b.org_air - a.org_air).map(company => (
                                    <tr key={company.company_id} className="hover:bg-white/5 transition duration-150">
                                        <td className="py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-md bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center text-xs font-bold text-white shadow-inner">
                                                    {company.ticker}
                                                </div>
                                                <div>
                                                    <div className="text-sm font-bold text-slate-200">{company.name}</div>
                                                    <div className="text-xs text-slate-500 capitalize">{company.sector.replace('_', ' ')}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="py-4">
                                            <span className={`px-2.5 py-1 rounded border text-xs font-semibold ${getScoreBadge(company.org_air)}`}>
                                                {company.org_air.toFixed(1)}
                                            </span>
                                        </td>
                                        <td className="py-4 hidden sm:table-cell">
                                            <div className={`text-sm font-medium flex items-center gap-1 ${getDeltaColor(company.delta_since_entry)}`}>
                                                {company.delta_since_entry >= 0 ? '↑' : '↓'}
                                                {Math.abs(company.delta_since_entry).toFixed(1)}
                                            </div>
                                        </td>
                                        <td className="py-4 text-right">
                                            <div className="text-sm text-slate-300 font-mono bg-slate-800/50 inline-block px-2 rounded">
                                                {company.synergy_score.toFixed(2)}x
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
