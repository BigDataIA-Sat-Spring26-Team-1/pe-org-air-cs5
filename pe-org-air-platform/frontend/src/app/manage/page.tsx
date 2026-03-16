"use client";

import { useState, useEffect } from "react";
import {
    Plus,
    Building2,
    Database,
    ArrowLeft,
    Loader2,
    CheckCircle2,
    AlertCircle,
    ChevronRight,
    Search
} from "lucide-react";
import Link from "next/link";

interface Industry {
    id: string;
    name: string;
    sector: string;
}

export default function ManagementPage() {
    const [industries, setIndustries] = useState<Industry[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // Form states
    const [industryName, setIndustryName] = useState("");
    const [industrySector, setIndustrySector] = useState("");

    const [companyName, setCompanyName] = useState("");
    const [companyTicker, setCompanyTicker] = useState("");
    const [selectedIndustryId, setSelectedIndustryId] = useState("");
    const [companyCik, setCompanyCik] = useState("");

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        fetchIndustries();
    }, [API_BASE]);

    async function fetchIndustries() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/industries/`);
            if (res.ok) {
                const data = await res.json();
                setIndustries(data);
                if (data.length > 0 && !selectedIndustryId) {
                    setSelectedIndustryId(data[0].id);
                }
            }
        } catch (err) {
            console.error("Failed to fetch industries:", err);
        } finally {
            setLoading(false);
        }
    }

    const handleAddIndustry = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setMessage(null);
        try {
            const res = await fetch(`${API_BASE}/api/v1/industries/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: industryName, sector: industrySector, h_r_base: 50 })
            });

            if (res.ok) {
                setMessage({ type: 'success', text: "Industry added successfully!" });
                setIndustryName("");
                setIndustrySector("");
                fetchIndustries();
            } else {
                const error = await res.json();
                setMessage({ type: 'error', text: error.detail || "Failed to add industry." });
            }
        } catch (err) {
            setMessage({ type: 'error', text: "Network error. Please try again." });
        } finally {
            setSubmitting(false);
        }
    };

    const handleAddCompany = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        setMessage(null);
        try {
            const res = await fetch(`${API_BASE}/api/v1/companies/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: companyName,
                    ticker: companyTicker,
                    industry_id: selectedIndustryId,
                    cik: companyCik || null,
                    position_factor: 0.5
                })
            });

            if (res.ok) {
                setMessage({ type: 'success', text: "Company added to portfolio!" });
                setCompanyName("");
                setCompanyTicker("");
                setCompanyCik("");
            } else {
                const error = await res.json();
                setMessage({ type: 'error', text: error.detail || "Failed to add company." });
            }
        } catch (err) {
            setMessage({ type: 'error', text: "Network error. Please try again." });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-8 space-y-8 max-w-5xl mx-auto">
            {/* Header */}
            <div>
                <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-all text-sm group w-fit mb-4">
                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                    Back to Dashboard
                </Link>
                <h2 className="text-3xl font-bold tracking-tight">Portfolio Management</h2>
                <p className="text-slate-400 mt-1">Configure your target universe and industry risk parameters.</p>
            </div>

            {message && (
                <div className={`p-4 rounded-xl border flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300 ${message.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                    }`}>
                    {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                    <span className="text-sm font-medium">{message.text}</span>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Add Industry */}
                <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl p-8 shadow-xl space-y-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center border border-purple-500/20">
                            <Database className="text-purple-400" size={20} />
                        </div>
                        <h3 className="text-xl font-bold">New Industry</h3>
                    </div>

                    <form onSubmit={handleAddIndustry} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Industry Name</label>
                            <input
                                required
                                value={industryName}
                                onChange={(e) => setIndustryName(e.target.value)}
                                placeholder="e.g. Specialty Chemicals"
                                className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Sector</label>
                            <input
                                required
                                value={industrySector}
                                onChange={(e) => setIndustrySector(e.target.value)}
                                placeholder="e.g. Industrials"
                                className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800/50 text-white py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2"
                        >
                            {submitting ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                            Create Industry
                        </button>
                    </form>
                </div>

                {/* Add Company */}
                <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl p-8 shadow-xl space-y-6">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                            <Building2 className="text-blue-400" size={20} />
                        </div>
                        <h3 className="text-xl font-bold">Add Company</h3>
                    </div>

                    <form onSubmit={handleAddCompany} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Company Name</label>
                            <input
                                required
                                value={companyName}
                                onChange={(e) => setCompanyName(e.target.value)}
                                placeholder="e.g. Caterpillar Inc."
                                className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Ticker</label>
                                <input
                                    required
                                    value={companyTicker}
                                    onChange={(e) => setCompanyTicker(e.target.value.toUpperCase())}
                                    placeholder="CAT"
                                    className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">CIK (Optional)</label>
                                <input
                                    value={companyCik}
                                    onChange={(e) => setCompanyCik(e.target.value)}
                                    placeholder="0000018492"
                                    className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">Industry</label>
                            <select
                                value={selectedIndustryId}
                                onChange={(e) => setSelectedIndustryId(e.target.value)}
                                className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 appearance-none"
                            >
                                {industries.map(ind => (
                                    <option key={ind.id} value={ind.id}>{ind.name} ({ind.sector})</option>
                                ))}
                                {industries.length === 0 && <option disabled>No industries found</option>}
                            </select>
                        </div>
                        <button
                            type="submit"
                            disabled={submitting || industries.length === 0}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800/50 text-white py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2"
                        >
                            {submitting ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />}
                            Track Company
                        </button>
                    </form>
                </div>
            </div>

            {/* Quick List */}
            <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
                <div className="p-6 border-b border-slate-800 bg-white/[0.01]">
                    <h3 className="font-bold flex items-center gap-2">
                        <Search size={18} className="text-slate-400" />
                        Existing Industries
                    </h3>
                </div>
                <div className="p-2 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {industries.map(ind => (
                        <div key={ind.id} className="p-4 bg-[#18181b]/50 rounded-2xl flex items-center justify-between border border-transparent hover:border-slate-800 transition-all">
                            <div>
                                <div className="text-sm font-semibold">{ind.name}</div>
                                <div className="text-[10px] text-slate-500 uppercase tracking-widest">{ind.sector}</div>
                            </div>
                            <ChevronRight size={14} className="text-slate-600" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
