"use client";

import { useState } from "react";
import {
    Search,
    Filter,
    FileText,
    Download,
    ChevronRight,
    ChevronDown,
    ExternalLink,
    Code,
    Table as TableIcon,
    Loader2,
    AlertCircle
} from "lucide-react";
import Link from "next/link";
import React from "react";

interface SecDocument {
    document_id: string;
    cik: string;
    company_name: string;
    filing_type: string;
    accession_number: string;
    s3_raw_path: string;
    processing_status: string;
    created_at: string;
}

export default function Explorer() {
    const [ticker, setTicker] = useState("");
    const [filingType, setFilingType] = useState("10-K");
    const [results, setResults] = useState<SecDocument[]>([]);
    const [loading, setLoading] = useState(false);
    const [viewMode, setViewMode] = useState<'table' | 'json'>('table');
    const [expandedRow, setExpandedRow] = useState<string | null>(null);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const baseUrl = API_BASE || window.location.origin;
            const url = new URL(`${baseUrl}/api/v1/documents`);
            if (ticker) url.searchParams.append("company", ticker);
            if (filingType) url.searchParams.append("filing_type", filingType);
            url.searchParams.append("limit", "50");

            const res = await fetch(url.toString());
            if (res.ok) {
                setResults(await res.json());
            }
        } catch (err) {
            console.error("Search failed:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 space-y-8">
            <div>
                <h2 className="text-3xl font-bold tracking-tight">SEC Explorer</h2>
                <p className="text-slate-400 mt-1">Direct access to the semantic engine's document registry.</p>
            </div>

            {/* Control Panel */}
            <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl p-6 shadow-xl">
                <form onSubmit={handleSearch} className="flex flex-wrap items-end gap-6">
                    <div className="flex-1 min-w-[200px] space-y-2">
                        <label className="text-sm font-medium text-slate-400">Company Ticker / Name</label>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                            <input
                                type="text"
                                value={ticker}
                                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                                placeholder="e.g. CAT, DE, UnitedHealth"
                                className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
                            />
                        </div>
                    </div>

                    <div className="w-48 space-y-2">
                        <label className="text-sm font-medium text-slate-400">Filing Type</label>
                        <select
                            value={filingType}
                            onChange={(e) => setFilingType(e.target.value)}
                            className="w-full bg-[#18181b] border border-slate-800 rounded-xl py-2.5 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50 appearance-none"
                        >
                            <option value="10-K">10-K (Annual)</option>
                            <option value="10-Q">10-Q (Quarterly)</option>
                            <option value="8-K">8-K (Current Event)</option>
                            <option value="DEF 14A">Proxy Statement</option>
                            <option value="">All Filings</option>
                        </select>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-8 py-2.5 rounded-xl transition-all font-medium flex items-center gap-2"
                    >
                        {loading ? <Loader2 size={18} className="animate-spin" /> : <Filter size={18} />}
                        Fetch Documents
                    </button>
                </form>
            </div>

            {/* Results Workspace */}
            <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
                <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-white/[0.02]">
                    <div className="flex gap-2 p-1 bg-[#18181b] rounded-lg">
                        <button
                            onClick={() => setViewMode('table')}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'table' ? 'bg-zinc-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                        >
                            <TableIcon size={14} /> Table View
                        </button>
                        <button
                            onClick={() => setViewMode('json')}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all ${viewMode === 'json' ? 'bg-zinc-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
                        >
                            <Code size={14} /> JSON Inspector
                        </button>
                    </div>
                    <span className="text-xs font-mono text-slate-500">{results.length} records found</span>
                </div>

                {results.length > 0 ? (
                    viewMode === 'table' ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-slate-800 text-slate-500 text-xs uppercase tracking-wider">
                                        <th className="px-6 py-4 font-semibold">Document ID</th>
                                        <th className="px-6 py-4 font-semibold">Company</th>
                                        <th className="px-6 py-4 font-semibold">Type</th>
                                        <th className="px-6 py-4 font-semibold">Status</th>
                                        <th className="px-6 py-4 font-semibold">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                    {results.map((doc) => (
                                        <React.Fragment key={doc.document_id}>
                                            <tr
                                                className={`hover:bg-white/[0.02] transition-colors cursor-pointer ${expandedRow === doc.document_id ? 'bg-blue-500/5' : ''}`}
                                                onClick={() => setExpandedRow(expandedRow === doc.document_id ? null : doc.document_id)}
                                            >
                                                <td className="px-6 py-4 font-mono text-sm text-blue-400">{doc.document_id}</td>
                                                <td className="px-6 py-4">
                                                    <div className="font-medium">{doc.company_name}</div>
                                                    <div className="text-xs text-slate-500">CIK: {doc.cik}</div>
                                                </td>
                                                <td className="px-6 py-4 text-sm">
                                                    <span className="bg-zinc-800 px-2 py-1 rounded text-xs font-bold border border-slate-700">{doc.filing_type}</span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className="flex items-center gap-1.5 text-xs font-medium text-green-400">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                                        {doc.processing_status}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="flex gap-2">
                                                        <a
                                                            href={`https://www.sec.gov/cgi-bin/browse-edgar?CIK=${doc.cik}&action=getcompany`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="p-2 hover:bg-zinc-800 rounded-lg text-slate-400 hover:text-white transition-all"
                                                            title="View on SEC Edgar"
                                                        >
                                                            <ExternalLink size={16} />
                                                        </a>
                                                    </div>
                                                </td>
                                            </tr>
                                            {expandedRow === doc.document_id && (
                                                <tr>
                                                    <td colSpan={6} className="bg-[#09090b] px-8 py-6">
                                                        <div className="grid grid-cols-3 gap-6">
                                                            <div className="space-y-4 col-span-2">
                                                                <h5 className="text-xs font-bold text-slate-500 uppercase">Semantic Metadata</h5>
                                                                <div className="grid grid-cols-2 gap-4">
                                                                    <div className="bg-[#18181b] p-3 rounded-xl border border-slate-800">
                                                                        <div className="text-[10px] text-slate-500 uppercase">Accession Number</div>
                                                                        <div className="text-sm font-mono mt-1">{doc.accession_number}</div>
                                                                    </div>
                                                                    <div className="bg-[#18181b] p-3 rounded-xl border border-slate-800">
                                                                        <div className="text-[10px] text-slate-500 uppercase">S3 Path</div>
                                                                        <div className="text-sm font-mono mt-1 truncate max-w-xs">{doc.s3_raw_path}</div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                            <div className="flex flex-col justify-end">
                                                                <Link
                                                                    href={`/playground?path=/api/v1/documents/${doc.document_id}/chunks&run=true`}
                                                                    className="w-full bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2"
                                                                >
                                                                    Inspect Semantic Chunks <ChevronRight size={16} />
                                                                </Link>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="p-6 bg-[#09090b] border-t border-slate-800">
                            <pre className="text-sm font-mono text-blue-300 overflow-auto max-h-[600px] p-4 bg-black/50 rounded-xl scrollbar-thin">
                                {JSON.stringify(results, null, 2)}
                            </pre>
                        </div>
                    )
                ) : (
                    <div className="p-24 text-center text-slate-500">
                        {loading ? (
                            <div className="flex flex-col items-center gap-4">
                                <Loader2 size={32} className="animate-spin text-blue-500" />
                                <p>Querying the semantic doc-store...</p>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center gap-4">
                                <FileText size={48} className="opacity-10" />
                                <p>No documents meta-indexed. Use the dashboard to run a collection.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
