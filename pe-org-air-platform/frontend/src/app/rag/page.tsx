"use client";

import React, { useState, useEffect, useRef } from "react";
import {
    Brain,
    Send,
    Loader2,
    Shield,
    ChevronRight,
    Database,
    Globe,
    Search,
    AlertCircle,
    CheckCircle2,
    Sparkles,
    FileText
} from "lucide-react";

interface Message {
    role: "user" | "assistant";
    content: string;
    evidence?: any[];
}

export default function RagAnalysis() {
    const [ticker, setTicker] = useState("NVDA");
    const [query, setQuery] = useState("");
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "assistant",
            content: "Welcome to the OrgAIR PE Intelligence Center. Enter a company ticker and ask a technical readiness question (e.g., about their AI infrastructure, talent pool, or cloud strategy)."
        }
    ]);
    const [loading, setLoading] = useState(false);
    const [ingesting, setIngesting] = useState(false);
    const [ingestedTickers, setIngestedTickers] = useState<Set<string>>(new Set());
    const [error, setError] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleIngest = async () => {
        if (!ticker) return;
        setIngesting(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/api/v1/rag/ingest?ticker=${ticker.toUpperCase()}`, {
                method: 'POST'
            });
            const data = await res.json();
            if (res.ok) {
                setIngestedTickers(prev => new Set(prev).add(ticker.toUpperCase()));
            } else {
                setError(data.detail || "Ingestion failed");
            }
        } catch (err) {
            setError("Failed to reach API");
        } finally {
            setIngesting(false);
        }
    };

    const handleSend = async () => {
        if (!query.trim() || !ticker.trim() || loading) return;

        const currentQuery = query;
        const currentTicker = ticker.toUpperCase();
        setQuery("");
        setMessages(prev => [...prev, { role: "user", content: currentQuery }]);
        setLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/api/v1/rag/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ticker: currentTicker,
                    query: currentQuery,
                    use_hyde: true,
                    top_k: 5
                })
            });

            const data = await res.json();

            if (res.ok) {
                setMessages(prev => [...prev, {
                    role: "assistant",
                    content: data.answer,
                    evidence: data.evidence
                }]);
            } else {
                setMessages(prev => [...prev, {
                    role: "assistant",
                    content: `Error: ${data.detail || "Request failed"}`
                }]);
                if (data.detail?.includes("Please run /ingest")) {
                    setError(`Company ${currentTicker} not ingested. Click the Load Data button.`);
                }
            }
        } catch (err) {
            setError("Network error occurred");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-[#09090b] text-slate-300 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/5 blur-[120px] rounded-full pointer-events-none" />
            <div className="absolute bottom-[-10%] left-[-10%] w-[50%] h-[50%] bg-purple-600/5 blur-[120px] rounded-full pointer-events-none" />

            {/* Header */}
            <header className="h-20 border-b border-slate-800/50 backdrop-blur-xl bg-black/20 flex items-center justify-between px-8 z-10">
                <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-blue-600/10 rounded-xl flex items-center justify-center border border-blue-500/20">
                        <Brain className="text-blue-500 w-6 h-6" />
                    </div>
                    <div>
                        <h1 className="text-lg font-black tracking-tight text-white uppercase">PE RAG Analysis</h1>
                        <p className="text-[10px] text-slate-500 font-bold tracking-widest uppercase">Intelligence-Augmented Due Diligence</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 bg-black/40 border border-slate-800 rounded-xl px-4 py-2">
                        <Database size={14} className="text-slate-500" />
                        <input
                            type="text"
                            value={ticker}
                            onChange={(e) => setTicker(e.target.value.toUpperCase())}
                            className="bg-transparent border-none outline-none text-xs font-black text-white w-16"
                            placeholder="TICKER"
                        />
                    </div>

                    <button
                        onClick={handleIngest}
                        disabled={ingesting || ingestedTickers.has(ticker.toUpperCase())}
                        className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-black text-[10px] tracking-widest transition-all ${ingestedTickers.has(ticker.toUpperCase())
                                ? "bg-green-500/10 text-green-500 border border-green-500/20"
                                : "bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_20px_rgba(37,99,235,0.2)]"
                            } disabled:opacity-50`}
                    >
                        {ingesting ? <Loader2 size={14} className="animate-spin" /> : ingestedTickers.has(ticker.toUpperCase()) ? <CheckCircle2 size={14} /> : <Database size={14} />}
                        {ingesting ? "INGESTING..." : ingestedTickers.has(ticker.toUpperCase()) ? "DATA READY" : "LOAD DATA"}
                    </button>
                </div>
            </header>

            {/* Main Chat Area */}
            <div className="flex-1 overflow-y-auto px-8 py-12 space-y-8 scrollbar-hide z-10">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
                        <div className={`max-w-[80%] ${msg.role === 'user'
                                ? 'bg-blue-600 text-white p-6 rounded-3xl rounded-tr-none shadow-xl'
                                : 'bg-[#121214] border border-slate-800/50 p-8 rounded-3xl rounded-tl-none shadow-2xl relative'
                            }`}>
                            {msg.role === 'assistant' && (
                                <div className="absolute top-4 right-6 flex items-center gap-2">
                                    <Sparkles size={12} className="text-blue-500" />
                                    <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">AI Agent</span>
                                </div>
                            )}

                            <div className={`text-sm leading-relaxed ${msg.role === 'user' ? 'font-medium' : 'text-slate-300'}`}>
                                {msg.content.split('\n').map((line, j) => (
                                    <p key={j} className={line.trim() ? "mb-4 last:mb-0" : "h-2"}>{line}</p>
                                ))}
                            </div>

                            {msg.evidence && msg.evidence.length > 0 && (
                                <div className="mt-8 pt-8 border-t border-slate-800/50 space-y-4">
                                    <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <Shield size={12} className="text-green-500" /> Sources & Verification
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {msg.evidence.map((ev, k) => (
                                            <div key={k} className="bg-black/40 border border-slate-800/50 rounded-2xl p-4 group hover:border-blue-500/30 transition-all cursor-help relative overflow-hidden">
                                                <div className="flex items-center gap-2 mb-2 text-blue-400">
                                                    <FileText size={12} />
                                                    <span className="text-[8px] font-black uppercase tracking-tighter">{ev.metadata?.source_type || 'Evidence'} [{k + 1}]</span>
                                                </div>
                                                <p className="text-[11px] text-slate-400 line-clamp-3 leading-relaxed">{ev.content}</p>
                                                <div className="absolute top-2 right-2 text-[8px] font-mono text-slate-600">
                                                    {(ev.score * 100).toFixed(1)}% match
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                {loading && (
                    <div className="flex justify-start animate-pulse">
                        <div className="bg-[#121214] border border-slate-800/50 p-6 rounded-3xl rounded-tl-none flex items-center gap-3">
                            <Loader2 size={16} className="animate-spin text-blue-500" />
                            <span className="text-xs font-bold text-slate-500 tracking-widest uppercase">Analyzing Intelligence...</span>
                        </div>
                    </div>
                )}
                {error && (
                    <div className="flex justify-center">
                        <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-6 py-3 rounded-2xl flex items-center gap-3 animate-in shake duration-500">
                            <AlertCircle size={14} />
                            <span className="text-xs font-bold uppercase tracking-tight">{error}</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Footer */}
            <footer className="p-8 pb-12 z-10">
                <div className="max-w-4xl mx-auto relative group">
                    <div className="absolute inset-0 bg-blue-600/10 blur-2xl rounded-3xl opacity-0 group-focus-within:opacity-100 transition-opacity" />
                    <div className="relative bg-[#121214] border border-slate-800 flex items-center gap-4 p-2 pl-6 rounded-[2rem] shadow-2xl backdrop-blur-2xl ring-1 ring-white/5">
                        <Search className="text-slate-500" size={18} />
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            placeholder={`Ask about ${ticker}'s technical readiness...`}
                            className="flex-1 bg-transparent border-none outline-none text-sm text-white py-4"
                        />
                        <button
                            onClick={handleSend}
                            disabled={loading || !query.trim()}
                            className="w-12 h-12 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 rounded-full flex items-center justify-center text-white transition-all active:scale-90 shadow-lg shadow-blue-600/20"
                        >
                            <Send size={18} />
                        </button>
                    </div>
                </div>
            </footer>
        </div>
    );
}
