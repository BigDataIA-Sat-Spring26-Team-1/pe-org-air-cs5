"use client";

import { useEffect, useState } from "react";
import {
    BarChart3,
    PieChart as PieChartIcon,
    TrendingUp,
    Building2,
    Filter,
    ChevronRight,
    Search,
    Activity,
    ArrowUpRight,
    ArrowDownRight,
    Info
} from "lucide-react";
import Link from "next/link";

interface IndustryDist {
    name: string;
    count: number;
}

interface CompanyMetric {
    id: string;
    name: string;
    ticker: string;
    signals: number;
    evidence: number;
    filings: number;
}

interface SignalDist {
    category: string;
    count: number;
}

export default function AnalyticsPage() {
    const [industryDist, setIndustryDist] = useState<IndustryDist[]>([]);
    const [companyMetrics, setCompanyMetrics] = useState<CompanyMetric[]>([]);
    const [signalDist, setSignalDist] = useState<SignalDist[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedIndustry, setSelectedIndustry] = useState<string>("All");

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        async function fetchMetrics() {
            try {
                const [indRes, compRes, sigRes] = await Promise.all([
                    fetch(`${API_BASE}/api/v1/metrics/industry-distribution`),
                    fetch(`${API_BASE}/api/v1/metrics/company-stats`),
                    fetch(`${API_BASE}/api/v1/metrics/signal-distribution`)
                ]);

                if (indRes.ok) setIndustryDist(await indRes.json());
                if (compRes.ok) setCompanyMetrics(await compRes.json());
                if (sigRes.ok) setSignalDist(await sigRes.json());
            } catch (err) {
                console.error("Failed to fetch metrics:", err);
            } finally {
                setLoading(false);
            }
        }

        fetchMetrics();
    }, [API_BASE]);

    const filteredMetrics = selectedIndustry === "All"
        ? companyMetrics
        : companyMetrics.filter(m => industryDist.find(i => i.name === selectedIndustry)); // This filter logic might need improvement if I had industry_id in metrics

    return (
        <div className="p-8 space-y-8 bg-[#030303] min-h-screen text-slate-200">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                        Intelligence Analytics
                    </h1>
                    <p className="text-slate-500 mt-2 flex items-center gap-2">
                        <Activity size={16} className="text-blue-500" />
                        Visualizing AI Maturity signals and SEC data depth across the portfolio.
                    </p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-[#0c0c0e] border border-slate-800 rounded-xl px-4 py-2">
                        <Filter size={16} className="text-slate-500" />
                        <select
                            className="bg-transparent border-none focus:outline-none text-sm font-medium"
                            value={selectedIndustry}
                            onChange={(e) => setSelectedIndustry(e.target.value)}
                        >
                            <option value="All">All Industries</option>
                            {industryDist.map(i => (
                                <option key={i.name} value={i.name}>{i.name}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Top Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricSummaryCard
                    label="Market Coverage"
                    value={industryDist.length.toString()}
                    subValue="Active Sectors"
                    icon={<PieChartIcon className="text-blue-500" />}
                    color="blue"
                />
                <MetricSummaryCard
                    label="Intelligence Depth"
                    value={companyMetrics.reduce((acc, curr) => acc + curr.signals, 0).toLocaleString()}
                    subValue="Total Signals"
                    icon={<TrendingUp className="text-purple-500" />}
                    color="purple"
                />
                <MetricSummaryCard
                    label="Evidence Density"
                    value={companyMetrics.reduce((acc, curr) => acc + curr.evidence, 0).toLocaleString()}
                    subValue="Verified Items"
                    icon={<BarChart3 className="text-green-500" />}
                    color="green"
                />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Industry Distribution Chart (Custom CSS/SVG) */}
                <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-xl font-bold flex items-center gap-2">
                            <Building2 size={20} className="text-blue-400" />
                            Portfolio Distribution
                        </h3>
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 bg-white/5 px-2 py-1 rounded">By Industry</span>
                    </div>

                    <div className="space-y-6">
                        {industryDist.map((item, idx) => {
                            const maxCount = Math.max(...industryDist.map(i => i.count));
                            const percentage = (item.count / maxCount) * 100;
                            return (
                                <div key={item.name} className="group">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-medium text-slate-300">{item.name}</span>
                                        <span className="text-sm font-bold text-blue-400">{item.count} Companies</span>
                                    </div>
                                    <div className="h-2 w-full bg-slate-800/50 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-1000 ease-out"
                                            style={{ width: `${loading ? 0 : percentage}%` }}
                                        />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Signal Category Distribution */}
                <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-xl font-bold flex items-center gap-2">
                            <Activity size={20} className="text-purple-400" />
                            Signal Intensity
                        </h3>
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 bg-white/5 px-2 py-1 rounded">By Category</span>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        {signalDist.map((item, idx) => (
                            <div key={item.category} className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] hover:bg-white/[0.04] transition-all group">
                                <div className="text-xs text-slate-500 uppercase tracking-widest mb-1 group-hover:text-purple-400 transition-colors">
                                    {item.category.replace(/_/g, ' ')}
                                </div>
                                <div className="text-2xl font-bold">{item.count.toLocaleString()}</div>
                            </div>
                        ))}
                    </div>

                    <div className="mt-8 p-4 rounded-2xl bg-blue-500/5 border border-blue-500/10 flex gap-4 items-start">
                        <Info className="text-blue-400 shrink-0 mt-0.5" size={18} />
                        <p className="text-xs text-slate-400 leading-relaxed">
                            Signal intensity reflects the volume of AI-related activity detected through job postings, patent filings, and technology stack updates.
                        </p>
                    </div>
                </div>
            </div>

            {/* Detailed Company Report */}
            <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
                <div className="p-8 border-b border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h3 className="text-xl font-bold">Company Intelligence Report</h3>
                        <p className="text-sm text-slate-500 mt-1">Granular breakdown of intelligence artifacts per tracked entity.</p>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search companies..."
                            className="bg-[#18181b] border border-slate-800 rounded-full py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 w-64"
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-white/[0.01] text-xs uppercase tracking-wider text-slate-500">
                                <th className="px-8 py-4 font-semibold">Entity</th>
                                <th className="px-8 py-4 font-semibold text-center">Signals</th>
                                <th className="px-8 py-4 font-semibold text-center">Evidence</th>
                                <th className="px-8 py-4 font-semibold text-center">SEC Filings</th>
                                <th className="px-8 py-4 font-semibold text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {filteredMetrics.map((company) => (
                                <tr key={company.id} className="hover:bg-white/[0.02] transition-colors group">
                                    <td className="px-8 py-5">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 bg-blue-600/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                                                <span className="font-bold text-xs text-blue-400">{company.ticker}</span>
                                            </div>
                                            <div>
                                                <div className="font-semibold">{company.name}</div>
                                                <div className="text-xs text-slate-500">UID: {company.id.substring(0, 8)}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-8 py-5 text-center">
                                        <span className="py-1 px-3 rounded-full bg-purple-500/10 text-purple-400 text-sm font-bold border border-purple-500/20">
                                            {company.signals}
                                        </span>
                                    </td>
                                    <td className="px-8 py-5 text-center">
                                        <span className="py-1 px-3 rounded-full bg-green-500/10 text-green-400 text-sm font-bold border border-green-500/20">
                                            {company.evidence}
                                        </span>
                                    </td>
                                    <td className="px-8 py-5 text-center">
                                        <span className="py-1 px-3 rounded-full bg-blue-500/10 text-blue-400 text-sm font-bold border border-blue-500/20">
                                            {company.filings}
                                        </span>
                                    </td>
                                    <td className="px-8 py-5 text-right">
                                        <Link
                                            href={`/audit/${company.id}`}
                                            className="inline-flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors text-sm font-medium"
                                        >
                                            Audit Details <ArrowUpRight size={14} />
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

function MetricSummaryCard({ label, value, subValue, icon, color }: { label: string; value: string; subValue: string; icon: React.ReactNode; color: 'blue' | 'purple' | 'green' }) {
    const colorMap = {
        blue: 'from-blue-500/10 to-transparent border-blue-500/20',
        purple: 'from-purple-500/10 to-transparent border-purple-500/20',
        green: 'from-green-500/10 to-transparent border-green-500/20',
    };

    return (
        <div className={`bg-gradient-to-br ${colorMap[color]} border rounded-3xl p-8 backdrop-blur-sm shadow-xl relative overflow-hidden group hover:scale-[1.02] transition-transform duration-300`}>
            <div className="absolute top-0 right-0 p-6 opacity-20 group-hover:scale-125 transition-transform duration-500">
                {icon}
            </div>
            <p className="text-slate-400 text-sm font-semibold tracking-wide uppercase">{label}</p>
            <div className="flex items-end gap-3 mt-4">
                <h3 className="text-5xl font-black">{value}</h3>
                <p className="text-slate-500 text-sm mb-2 font-medium">{subValue}</p>
            </div>
        </div>
    );
}
