"use client";

import { useState, useEffect } from "react";
import {
    Plus,
    Trash2,
    Play,
    ArrowLeft,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Building2,
    History
} from "lucide-react";
import Link from "next/link";

interface Target {
    ticker: string;
    name: string;
    sector: string;
}

export default function CollectionPage() {
    const [targets, setTargets] = useState<Target[]>([
        { ticker: "", name: "", sector: "Technology" }
    ]);
    const [submitting, setSubmitting] = useState(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
    const [stats, setStats] = useState<any>(null);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/v1/evidence/stats`);
                if (res.ok) setStats(await res.json());
            } catch (err) {
                console.error("Failed to fetch stats");
            }
        };
        fetchStats();
        const interval = setInterval(fetchStats, 5000);
        return () => clearInterval(interval);
    }, [API_BASE]);

    const addRow = () => {
        setTargets([...targets, { ticker: "", name: "", sector: "Technology" }]);
    };

    const removeRow = (index: number) => {
        if (targets.length > 1) {
            setTargets(targets.filter((_, i) => i !== index));
        }
    };

    const updateRow = (index: number, field: keyof Target, value: string) => {
        const newTargets = [...targets];
        newTargets[index][field] = field === 'ticker' ? value.toUpperCase() : value;
        setTargets(newTargets);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Filter out incomplete rows
        const validTargets = targets.filter(t => t.ticker && t.sector);
        if (validTargets.length === 0) {
            setMessage({ type: 'error', text: "Please provide at least one ticker and industry." });
            return;
        }

        setSubmitting(true);
        setMessage(null);

        try {
            const res = await fetch(`${API_BASE}/api/v1/evidence/collect`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ targets: validTargets })
            });

            if (res.ok) {
                setMessage({ type: 'success', text: "Batch collection initiated successfully!" });
                setTargets([{ ticker: "", name: "", sector: "Technology" }]);
            } else {
                const error = await res.json();
                setMessage({ type: 'error', text: error.message || "Failed to start collection." });
            }
        } catch (err) {
            setMessage({ type: 'error', text: "Network error. Please try again." });
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-[#050507] text-white p-8 lg:p-12 space-y-12">
            <div>
                <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-all text-sm group w-fit mb-4">
                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                    Back to Dashboard
                </Link>
                <div className="flex justify-between items-end">
                    <div>
                        <h2 className="text-4xl font-black tracking-tight">Batch Collector</h2>
                        <p className="text-slate-400 mt-2 font-medium">Orchestrate SEC and Signal collection for multiple targets at once.</p>
                    </div>
                    {stats?.status === "running" && (
                        <div className="bg-blue-600/10 border border-blue-500/20 px-4 py-2 rounded-xl flex items-center gap-3 animate-pulse">
                            <Loader2 size={16} className="animate-spin text-blue-400" />
                            <span className="text-[10px] font-black uppercase tracking-widest text-blue-400">Processing Active</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-12">
                <div className="xl:col-span-2 space-y-8">
                    {message && (
                        <div className={`p-6 rounded-2xl border flex items-center gap-4 animate-in fade-in slide-in-from-top-2 duration-300 ${message.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'
                            }`}>
                            {message.type === 'success' ? <CheckCircle2 size={24} /> : <AlertCircle size={24} />}
                            <span className="font-bold">{message.text}</span>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="bg-[#0c0c0e] border border-white/5 rounded-[2rem] overflow-hidden shadow-2xl">
                            <table className="w-full text-left">
                                <thead className="bg-white/[0.02] border-b border-white/5">
                                    <tr>
                                        <th className="px-8 py-5 text-[10px] font-black uppercase tracking-widest text-slate-500">Ticker</th>
                                        <th className="px-8 py-5 text-[10px] font-black uppercase tracking-widest text-slate-500">Company Name (Optional)</th>
                                        <th className="px-8 py-5 text-[10px] font-black uppercase tracking-widest text-slate-500">Industry / Sector</th>
                                        <th className="px-8 py-5 w-20"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/[0.03]">
                                    {targets.map((target, index) => (
                                        <tr key={index} className="group hover:bg-white/[0.01] transition-colors">
                                            <td className="px-8 py-6">
                                                <input
                                                    required
                                                    value={target.ticker}
                                                    onChange={(e) => updateRow(index, 'ticker', e.target.value)}
                                                    placeholder="AAPL"
                                                    className="w-full bg-black/40 border border-white/5 rounded-xl py-3 px-4 text-sm font-bold focus:outline-none focus:border-blue-500/50 transition-all uppercase"
                                                />
                                            </td>
                                            <td className="px-8 py-6">
                                                <input
                                                    value={target.name}
                                                    onChange={(e) => updateRow(index, 'name', e.target.value)}
                                                    placeholder="Apple Inc."
                                                    className="w-full bg-black/40 border border-white/5 rounded-xl py-3 px-4 text-sm font-bold focus:outline-none focus:border-blue-500/50 transition-all"
                                                />
                                            </td>
                                            <td className="px-8 py-6">
                                                <input
                                                    required
                                                    value={target.sector}
                                                    onChange={(e) => updateRow(index, 'sector', e.target.value)}
                                                    placeholder="Technology"
                                                    className="w-full bg-black/40 border border-white/5 rounded-xl py-3 px-4 text-sm font-bold focus:outline-none focus:border-blue-500/50 transition-all"
                                                />
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <button
                                                    type="button"
                                                    onClick={() => removeRow(index)}
                                                    className="p-3 text-slate-600 hover:text-red-400 transition-colors"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            <div className="p-8 bg-white/[0.01] flex justify-between items-center">
                                <button
                                    type="button"
                                    onClick={addRow}
                                    className="flex items-center gap-2 text-blue-400 hover:text-blue-300 font-black text-[10px] tracking-[0.2em] transition-all"
                                >
                                    <Plus size={16} /> ADD ANOTHER TARGET
                                </button>

                                <button
                                    type="submit"
                                    disabled={submitting || stats?.status === "running"}
                                    className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/40 text-white px-10 py-4 rounded-xl transition-all font-black text-xs tracking-widest flex items-center gap-3 shadow-[0_0_40px_rgba(37,99,235,0.2)]"
                                >
                                    {submitting ? <Loader2 size={16} animate-spin /> : <Play size={16} />}
                                    {submitting ? "INITIATING..." : "EXECUTE BATCH COLLECTION"}
                                </button>
                            </div>
                        </div>
                    </form>
                </div>

                <div className="space-y-8">
                    <div className="bg-[#0c0c0e] border border-white/5 rounded-[2.5rem] p-8 shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-600/5 blur-[40px] rounded-full" />
                        <h3 className="text-sm font-black text-white uppercase tracking-[0.3em] mb-8 flex items-center gap-3">
                            <History size={16} className="text-blue-500" />
                            Pipeline Status
                        </h3>

                        <div className="space-y-6">
                            <StatusItem label="Current Status" value={stats?.status || "IDLE"} highlight={stats?.status === "running"} />
                            <StatusItem label="Processed" value={`${stats?.companies || 0} Companies`} />
                            <StatusItem label="Data Found" value={`${stats?.signals || 0} Signals`} />
                            <StatusItem label="SEC Docs" value={`${stats?.documents || 0} Filings`} />
                            <StatusItem label="Errors" value={stats?.errors?.toString() || "0"} color={stats?.errors > 0 ? "text-red-400" : ""} />
                        </div>
                    </div>

                    <div className="bg-gradient-to-br from-blue-600/10 to-transparent border border-blue-500/10 rounded-[2.5rem] p-8">
                        <h4 className="font-black text-xs text-blue-400 uppercase tracking-widest mb-4">Pro Tip</h4>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Batch collection runs asynchronously. You can leave this page or close the browser and the pipeline will continue processing in the background.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatusItem({ label, value, highlight, color }: { label: string; value: string; highlight?: boolean, color?: string }) {
    return (
        <div className="flex justify-between items-center py-2 border-b border-white/5">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{label}</span>
            <span className={`text-sm font-black tracking-tight ${highlight ? 'text-blue-400 animate-pulse' : color || 'text-white'}`}>{value}</span>
        </div>
    );
}
