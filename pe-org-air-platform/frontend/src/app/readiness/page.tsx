"use client";

import React, { useEffect, useState } from "react";
import {
    TrendingUp,
    FileText,
    Database,
    LayoutGrid,
    Activity,
    Award,
    BarChart3,
    Loader2,
    ChevronRight,
    ShieldCheck,
    Zap,
} from "lucide-react";

interface LeaderboardItem {
    company_id: string;
    ticker: string;
    technology_hiring_score: number;
    innovation_activity_score: number;
    digital_presence_score: number;
    leadership_signals_score: number;
    composite_score: number;
    signal_count: number;
}

interface DocItem {
    ticker: string;
    company: string;
    "10-k": number;
    "10-q": number;
    "8-k": number;
    "def 14a": number;
    total_docs: number;
}

interface ChunkItem {
    ticker: string;
    company: string;
    total_docs: number;
    total_chunks: number;
    total_words: number;
}

interface SectorItem {
    sector: string;
    avg_hiring: number;
    avg_innovation: number;
    avg_digital: number;
    avg_leadership: number;
    avg_composite: number;
    companies_count: number;
}

interface DeepAssessmentItem {
    company_id: string;
    ticker: string;
    company_name: string;
    v_r_score: number;
    h_r_score: number;
    synergy_score: number;
    org_air_score: number;
    confidence_score: number;
    assessment_date: string;
}

interface ReadinessReport {
    leaderboard: LeaderboardItem[];
    documents: DocItem[];
    chunks: ChunkItem[];
    sectors: SectorItem[];
    deep_assessments: DeepAssessmentItem[];
}

export default function ReadinessPage() {
    const [report, setReport] = useState<ReadinessReport | null>(null);
    const [loading, setLoading] = useState(true);

    const API_BASE = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) || "";

    useEffect(() => {
        async function fetchReport() {
            try {
                const res = await fetch(`${API_BASE}/api/v1/metrics/readiness-report`);
                if (res.ok) {
                    setReport(await res.json());
                }
            } catch (err) {
                console.error("Failed to fetch readiness report:", err);
            } finally {
                setLoading(false);
            }
        }
        fetchReport();
    }, [API_BASE]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-[#050507]">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
                    <span className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-500">Generating Report</span>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-[#050507] text-slate-100 p-8 lg:p-12 space-y-16 relative overflow-hidden">
            {/* Background Decor */}
            <div className="absolute top-[-10%] right-[-5%] w-[50%] h-[50%] bg-blue-600/5 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute bottom-[-10%] left-[-5%] w-[40%] h-[40%] bg-indigo-600/5 blur-[120px] rounded-full pointer-events-none" />

            {/* Header */}
            <div className="relative z-10">
                <div className="flex items-center gap-3 text-blue-500 mb-4">
                    <span className="h-[1px] w-12 bg-blue-500/50" />
                    <span className="text-[10px] font-black uppercase tracking-[0.4em]">Strategic Assessment</span>
                </div>
                <h1 className="text-6xl font-black text-white tracking-tighter mb-4">AI Readiness</h1>
                <p className="text-slate-500 text-xl max-w-2xl font-medium">
                    Comprehensive benchmark of technological parity and innovation velocity across your portfolio.
                </p>
            </div>

            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 relative z-10">
                <ReportSummaryCard
                    label="Leaderboard Rank"
                    value={report?.leaderboard[0]?.ticker || "---"}
                    detail="Market Leader"
                    icon={<Award className="text-blue-400" />}
                    color="blue"
                />
                <ReportSummaryCard
                    label="Total Evidence"
                    value={report?.leaderboard.reduce((acc, curr) => acc + curr.signal_count, 0).toString() || "0"}
                    detail="Verified Signals"
                    icon={<Activity className="text-purple-400" />}
                    color="purple"
                />
                <ReportSummaryCard
                    label="Total Chunks"
                    value={report?.chunks.reduce((acc, curr) => acc + curr.total_chunks, 0).toLocaleString() || "0"}
                    detail="Semantic Nodes"
                    icon={<LayoutGrid className="text-emerald-400" />}
                    color="emerald"
                />
                <ReportSummaryCard
                    label="Corpus Coverage"
                    value={report?.documents.reduce((acc, curr) => acc + curr.total_docs, 0).toString() || "0"}
                    detail="Intelligence Docs"
                    icon={<Database className="text-amber-400" />}
                    color="amber"
                />
            </div>

            {/* Leaderboard Section */}
            <section className="relative z-10 space-y-8">
                <div className="flex items-center justify-between">
                    <h2 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
                        <TrendingUp size={32} className="text-blue-500" />
                        AI Readiness Leaderboard
                    </h2>
                    <div className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-[10px] font-black tracking-widest uppercase">
                        Aggregated Benchmarks
                    </div>
                </div>

                <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl backdrop-blur-xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="bg-white/[0.02] border-b border-white/5">
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Rank</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Company</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Hiring (30%)</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Innovation (25%)</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Digital (25%)</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Leadership (20%)</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-white">Composite</th>
                                    <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-right">Signals</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.03]">
                                {report?.leaderboard.map((item, idx) => (
                                    <tr key={item.company_id} className="hover:bg-white/[0.02] transition-colors group">
                                        <td className="px-8 py-6">
                                            <span className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-xs ${idx === 0 ? "bg-amber-500/20 text-amber-500 border border-amber-500/30" : "bg-white/5 text-slate-500"}`}>
                                                {idx + 1}
                                            </span>
                                        </td>
                                        <td className="px-8 py-6">
                                            <div className="flex items-center gap-4">
                                                <div className="px-2 py-1 bg-blue-600/10 border border-blue-500/20 rounded text-[10px] font-black text-blue-400 min-w-[40px] text-center">
                                                    {item.ticker}
                                                </div>
                                                <span className="font-bold text-slate-200 group-hover:text-blue-400 transition-colors uppercase tracking-tight">{item.ticker === 'DE' ? 'Deere & Company' : item.ticker}</span>
                                            </div>
                                        </td>
                                        <td className="px-8 py-6">
                                            <ScoreDisplay value={item.technology_hiring_score} />
                                        </td>
                                        <td className="px-8 py-6">
                                            <ScoreDisplay value={item.innovation_activity_score} />
                                        </td>
                                        <td className="px-8 py-6">
                                            <ScoreDisplay value={item.digital_presence_score} />
                                        </td>
                                        <td className="px-8 py-6">
                                            <ScoreDisplay value={item.leadership_signals_score} />
                                        </td>
                                        <td className="px-8 py-6">
                                            <span className="text-xl font-black text-white tracking-widest">{item.composite_score.toFixed(1)}</span>
                                        </td>
                                        <td className="px-8 py-6 text-right">
                                            <span className="text-xs font-black text-blue-500">{item.signal_count}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            {/* Deep Intelligence Assessments Section */}
            {report?.deep_assessments && report.deep_assessments.length > 0 && (
                <section className="relative z-10 space-y-8">
                    <div className="flex items-center justify-between">
                        <h2 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
                            <ShieldCheck size={32} className="text-indigo-500" />
                            Deep Intelligence Assessments
                        </h2>
                        <div className="px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-[10px] font-black tracking-widest uppercase text-indigo-400">
                            High Fidelity Audit (INTEGRATED_CS3)
                        </div>
                    </div>

                    <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl backdrop-blur-xl">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead>
                                    <tr className="bg-white/[0.02] border-b border-white/5">
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Company</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">V-R (Readiness)</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">H-R (Context)</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Synergy</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-white">Org-AIR Score</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Confidence</th>
                                        <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-right">Date</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/[0.03]">
                                    {report.deep_assessments.map((item) => (
                                        <tr key={item.company_id} className="hover:bg-white/[0.02] transition-colors group">
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-4">
                                                    <div className="px-2 py-1 bg-indigo-600/10 border border-indigo-500/20 rounded text-[10px] font-black text-indigo-400 min-w-[40px] text-center">
                                                        {item.ticker}
                                                    </div>
                                                    <span className="font-bold text-slate-200 group-hover:text-indigo-400 transition-colors uppercase tracking-tight">{item.company_name}</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6">
                                                <ScoreDisplay value={item.v_r_score} />
                                            </td>
                                            <td className="px-8 py-6">
                                                <ScoreDisplay value={item.h_r_score} />
                                            </td>
                                            <td className="px-8 py-6">
                                                <ScoreDisplay value={item.synergy_score} />
                                            </td>
                                            <td className="px-8 py-6">
                                                <span className="text-2xl font-black text-white tracking-widest bg-gradient-to-r from-indigo-400 to-blue-400 bg-clip-text text-transparent">
                                                    {(item.org_air_score || 0).toFixed(1)}
                                                </span>
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-2">
                                                    <Zap size={14} className={item.confidence_score > 0.8 ? "text-amber-500" : "text-slate-600"} />
                                                    <span className="text-xs font-bold text-slate-400">{((item.confidence_score || 0) * 100).toFixed(0)}%</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <span className="text-[10px] font-black text-slate-500 uppercase">{new Date(item.assessment_date).toLocaleDateString()}</span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>
            )}

            {/* Docs & Chunks Split */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-12 relative z-10">
                {/* Documents Distribution */}
                <section className="space-y-8">
                    <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-4">
                        <FileText size={24} className="text-purple-500" />
                        Documents by Company
                    </h2>
                    <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2rem] overflow-hidden shadow-2xl backdrop-blur-xl">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="bg-white/[0.02] border-b border-white/5">
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500">Ticker</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">10-K</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">10-Q</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">8-K</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">DEF 14A</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-white text-right">Total</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.03]">
                                {report?.documents.map((item) => (
                                    <tr key={item.ticker} className="hover:bg-white/[0.01] transition-colors">
                                        <td className="px-6 py-4"><span className="text-xs font-black text-blue-400">{item.ticker}</span></td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item["10-k"]}</td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item["10-q"]}</td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item["8-k"]}</td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item["def 14a"]}</td>
                                        <td className="px-6 py-4 text-right"><span className="text-xs font-black text-white">{item.total_docs}</span></td>
                                    </tr>
                                ))}
                                <tr className="bg-white/[0.03] font-black">
                                    <td className="px-6 py-4 uppercase tracking-widest text-[9px]">Total</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.documents.reduce((a, c) => a + c["10-k"], 0)}</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.documents.reduce((a, c) => a + c["10-q"], 0)}</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.documents.reduce((a, c) => a + c["8-k"], 0)}</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.documents.reduce((a, c) => a + c["def 14a"], 0)}</td>
                                    <td className="px-6 py-4 text-right text-xs text-blue-500">{report?.documents.reduce((a, c) => a + c.total_docs, 0)}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </section>

                {/* Chunks Analysis */}
                <section className="space-y-8">
                    <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-4">
                        <LayoutGrid size={24} className="text-emerald-500" />
                        Chunks by Company
                    </h2>
                    <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2rem] overflow-hidden shadow-2xl backdrop-blur-xl">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="bg-white/[0.02] border-b border-white/5">
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500">Ticker</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">Docs</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-slate-500 text-center">Total Chunks</th>
                                    <th className="px-6 py-4 text-[9px] font-black uppercase tracking-widest text-white text-right">Token Count</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/[0.03]">
                                {report?.chunks.map((item) => (
                                    <tr key={item.ticker} className="hover:bg-white/[0.01] transition-colors">
                                        <td className="px-6 py-4"><span className="text-xs font-black text-blue-400">{item.ticker}</span></td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item.total_docs}</td>
                                        <td className="px-6 py-4 text-center text-xs font-medium text-slate-400">{item.total_chunks}</td>
                                        <td className="px-6 py-4 text-right"><span className="text-xs font-black text-white">{item.total_words?.toLocaleString()}</span></td>
                                    </tr>
                                ))}
                                <tr className="bg-white/[0.03] font-black">
                                    <td className="px-6 py-4 uppercase tracking-widest text-[9px]">Total</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.chunks.reduce((a, c) => a + c.total_docs, 0)}</td>
                                    <td className="px-6 py-4 text-center text-xs">{report?.chunks.reduce((a, c) => a + c.total_chunks, 0)}</td>
                                    <td className="px-6 py-4 text-right text-xs text-blue-500">{report?.chunks.reduce((a, c) => a + c.total_words, 0).toLocaleString()}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </section>
            </div>

            {/* Sector Analysis */}
            <section className="relative z-10 space-y-8">
                <h2 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
                    <BarChart3 size={32} className="text-amber-500" />
                    Sector Analysis
                </h2>
                <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl backdrop-blur-xl mb-12">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-white/[0.02] border-b border-white/5">
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500">Sector</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-center">Avg Hiring</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-center">Avg Innovation</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-center">Avg Digital</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-center">Avg Leadership</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-white text-center">Avg Composite</th>
                                <th className="px-8 py-6 text-[10px] font-black uppercase tracking-widest text-slate-500 text-right">Companies</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.03]">
                            {report?.sectors.map((item) => (
                                <tr key={item.sector} className="hover:bg-white/[0.02] transition-colors">
                                    <td className="px-8 py-6">
                                        <span className="font-bold text-slate-200 uppercase tracking-tighter">{item.sector}</span>
                                    </td>
                                    <td className="px-8 py-6 text-center text-slate-400 font-medium">{item.avg_hiring.toFixed(1)}</td>
                                    <td className="px-8 py-6 text-center text-slate-400 font-medium">{item.avg_innovation.toFixed(1)}</td>
                                    <td className="px-8 py-6 text-center text-slate-400 font-medium">{item.avg_digital.toFixed(1)}</td>
                                    <td className="px-8 py-6 text-center text-slate-400 font-medium">{item.avg_leadership.toFixed(1)}</td>
                                    <td className="px-8 py-6 text-center"><span className="text-lg font-black text-white tracking-widest">{item.avg_composite.toFixed(1)}</span></td>
                                    <td className="px-8 py-6 text-right"><span className="text-xs font-black text-blue-500">{item.companies_count}</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
}

function ReportSummaryCard({ label, value, detail, icon, color }: { label: string; value: string; detail: string; icon: React.ReactNode; color: string }) {
    const colorMap: Record<string, string> = {
        blue: "bg-blue-600/10 border-blue-500/20",
        purple: "bg-purple-600/10 border-purple-500/20",
        emerald: "bg-emerald-600/10 border-emerald-500/20",
        amber: "bg-amber-600/10 border-amber-500/20",
    };

    return (
        <div className="bg-[#0c0c0e]/80 border border-white/5 rounded-[2rem] p-8 shadow-xl backdrop-blur-3xl group hover:border-white/10 transition-all">
            <div className="flex justify-between items-start mb-6">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em]">{label}</p>
                <div className={`p-4 rounded-xl border group-hover:scale-110 transition-transform duration-500 ${colorMap[color]}`}>
                    {icon}
                </div>
            </div>
            <div>
                <h3 className="text-4xl font-black text-white tracking-tighter mb-2">{value}</h3>
                <p className="text-[9px] font-black uppercase tracking-widest text-slate-600 flex items-center gap-2">
                    <ChevronRight size={10} className="text-slate-800" />
                    {detail}
                </p>
            </div>
        </div>
    );
}

function ScoreDisplay({ value }: { value: number }) {
    return (
        <div className="flex items-center gap-3">
            <div className="w-16 h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                    className="h-full bg-blue-500/50 rounded-full"
                    style={{ width: `${value}%` }}
                />
            </div>
            <span className="text-xs font-bold text-slate-400 min-w-[30px]">{value.toFixed(1)}</span>
        </div>
    );
}
