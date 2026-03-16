"use client";

import { useEffect, useState, use } from "react";
import {
    ArrowLeft,
    TrendingUp,
    Target as TargetIcon,
    Code,
    Table as TableIcon,
    Activity,
    Cpu,
    Brain,
    Globe,
    Briefcase,
    PieChart,
    Calendar,
    ExternalLink,
    ChevronDown,
    Loader2,
    FileText,
    ShieldCheck,
    Search,
    Download,
    Users,
    MessageSquare,
    Smile
} from "lucide-react";
import Link from "next/link";

interface Signal {
    id: string;
    category: string;
    source: string;
    signal_date: string;
    normalized_score: number;
    confidence: number;
    raw_value: string;
    metadata: any;
}

interface Evidence {
    id: string;
    title: string;
    source: string;
    evidence_date: string;
    category: string;
    url?: string;
}

interface Document {
    document_id: string;
    filing_type: string;
    company_name: string;
    processing_status: string;
    cik?: string;
}

interface Company {
    id: string;
    name: string;
    ticker: string;
    position_factor: number;
}

interface SignalSummary {
    composite_score: number;
    technology_hiring_score: number;
    innovation_activity_score: number;
    digital_presence_score: number;
    leadership_signals_score: number;
}

interface CompanyMetrics {
    signals: number;
    evidence: number;
    filings: number;
}

interface CultureScores {
    innovation_score: number;
    data_driven_score: number;
    ai_awareness_score: number;
    change_readiness_score: number;
    overall_sentiment: number;
    review_count: number;
    avg_rating: number;
    confidence: number;
    positive_keywords_found: string[];
    negative_keywords_found: string[];
}

interface GlassdoorReview {
    id: string;
    review_date: string;
    rating: number;
    title: string;
    pros: string;
    cons: string;
    job_title: string;
    is_current_employee: boolean;
}

export default function AuditPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: companyId } = use(params);
    const [signals, setSignals] = useState<Signal[]>([]);
    const [evidence, setEvidence] = useState<Evidence[]>([]);
    const [documents, setDocuments] = useState<Document[]>([]);
    const [culture, setCulture] = useState<CultureScores | null>(null);
    const [gdReviews, setGdReviews] = useState<GlassdoorReview[]>([]);
    const [company, setCompany] = useState<Company | null>(null);
    const [summary, setSummary] = useState<SignalSummary | null>(null);
    const [metrics, setMetrics] = useState<CompanyMetrics | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'signals' | 'evidence' | 'filings' | 'culture'>('signals');
    const [evidencePage, setEvidencePage] = useState(1);
    const [filingsPage, setFilingsPage] = useState(1);
    const PAGE_SIZE = 10;

    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

    useEffect(() => {
        async function fetchData() {
            try {
                const compRes = await fetch(`${API_BASE}/api/v1/companies/${companyId}`);
                if (!compRes.ok) return;
                const companyData = await compRes.json();
                setCompany(companyData);

                const [sigRes, evRes, docRes, sumRes, metRes, culRes, revRes] = await Promise.all([
                    fetch(`${API_BASE}/api/v1/signals/?ticker=${companyData.ticker}`),
                    fetch(`${API_BASE}/api/v1/signals/evidence?company_id=${companyId}&limit=${PAGE_SIZE}&offset=${(evidencePage - 1) * PAGE_SIZE}`),
                    fetch(`${API_BASE}/api/v1/documents?company=${companyData.ticker}&limit=${PAGE_SIZE}&offset=${(filingsPage - 1) * PAGE_SIZE}`),
                    fetch(`${API_BASE}/api/v1/signals/summary?ticker=${companyData.ticker}`),
                    fetch(`${API_BASE}/api/v1/metrics/company-stats?company_id=${companyId}`),
                    fetch(`${API_BASE}/api/v1/signals/culture/${companyData.ticker}`),
                    fetch(`${API_BASE}/api/v1/signals/culture/reviews/${companyData.ticker}?limit=20`)
                ]);

                if (sigRes.ok) setSignals(await sigRes.json());
                if (evRes.ok) setEvidence(await evRes.json());
                if (docRes.ok) {
                    const docData = await docRes.json();
                    setDocuments(docData || []);
                }
                if (sumRes.ok) setSummary(await sumRes.json());
                if (metRes.ok) {
                    const metData = await metRes.json();
                    setMetrics(metData[0] || null);
                }
                if (culRes.ok) {
                    const culData = await culRes.json();
                    if (!culData.message) setCulture(culData);
                }
                if (revRes.ok) setGdReviews(await revRes.json());

            } catch (err) {
                console.error("Failed to fetch audit data:", err);
            } finally {
                setLoading(false);
            }
        }

        if (companyId) fetchData();
    }, [companyId, API_BASE, evidencePage, filingsPage]);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    const compositeScore = summary?.composite_score?.toFixed(1) || "0.0";
    const confidence = (signals.reduce((acc, s) => acc + s.confidence, 0) / (signals.length || 1) * 100).toFixed(0);

    return (
        <div className="p-8 space-y-8 max-w-7xl mx-auto min-h-screen">
            {/* Navigation */}
            <div className="flex justify-between items-center">
                <Link href="/" className="flex items-center gap-2 text-slate-400 hover:text-white transition-all text-sm group w-fit">
                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                    Back to Dashboard
                </Link>
                <div className="text-[10px] text-zinc-500 font-mono tracking-widest uppercase">Target ID: {companyId}</div>
            </div>

            {/* Profile Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 bg-[#0c0c0e] border border-slate-800 p-8 rounded-[2.5rem] shadow-2xl relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 blur-[100px] pointer-events-none" />

                <div className="flex items-center gap-8 relative z-10">
                    <div className="w-24 h-24 bg-gradient-to-br from-blue-600 to-blue-400 rounded-3xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <span className="text-4xl font-black text-white">{company?.ticker}</span>
                    </div>
                    <div>
                        <div className="flex items-center gap-3">
                            <h1 className="text-5xl font-black tracking-tighter text-white">{company?.name}</h1>
                            <ShieldCheck className="text-blue-400" size={24} />
                        </div>
                        <div className="flex gap-4 mt-3 text-slate-500 text-sm font-medium">
                            <span className="flex items-center gap-1.5"><Calendar size={14} /> Full Audit Active</span>
                            <span className="flex items-center gap-1.5 text-blue-400"><Globe size={14} /> Global Discovery Enabled</span>
                        </div>
                    </div>
                </div>

                <div className="flex gap-8 relative z-10">
                    <div className="text-right">
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Positioning</div>
                        <div className="text-4xl font-black text-white">{(company?.position_factor || 0) * 100}%</div>
                    </div>
                    <div className="w-[1px] h-12 bg-slate-800 self-center" />
                    <div className="text-right">
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Intelligence Cap</div>
                        <div className="text-4xl font-black text-blue-400">{compositeScore}</div>
                    </div>
                </div>
            </div>

            {/* Top Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <MiniStats cardColor="blue" label="Tech Score" value={compositeScore} icon={<Cpu size={20} />} />
                <MiniStats cardColor="purple" label="Confidence" value={`${confidence}%`} icon={<Brain size={20} />} />
                <MiniStats cardColor="green" label="Verified Evidence" value={(metrics?.evidence || 0).toString()} icon={<ShieldCheck size={20} />} />
                <MiniStats cardColor="orange" label="SEC Filings" value={(metrics?.filings || 0).toString()} icon={<FileText size={20} />} />
            </div>

            {/* Tabs & Content */}
            <div className="space-y-6">
                <div className="flex gap-2 p-1 bg-[#18181b] rounded-2xl border border-slate-800 w-fit">
                    <TabButton active={activeTab === 'signals'} onClick={() => setActiveTab('signals')} label="Signals" icon={<Activity size={16} />} />
                    <TabButton active={activeTab === 'evidence'} onClick={() => setActiveTab('evidence')} label="Evidence" icon={<ShieldCheck size={16} />} />
                    <TabButton active={activeTab === 'filings'} onClick={() => setActiveTab('filings')} label="SEC Filings" icon={<FileText size={16} />} />
                    <TabButton active={activeTab === 'culture'} onClick={() => setActiveTab('culture')} label="Workforce" icon={<Users size={16} />} />
                </div>

                <div className="bg-[#0c0c0e] border border-slate-800 rounded-3xl overflow-hidden shadow-2xl min-h-[500px]">
                    {activeTab === 'signals' && (
                        <div className="divide-y divide-slate-800/50">
                            {signals.map(s => (
                                <SignalRow key={s.id} signal={s} />
                            ))}
                            {signals.length === 0 && <EmptyState label="No signals collected" />}
                        </div>
                    )}

                    {activeTab === 'evidence' && (
                        <div>
                            <div className="divide-y divide-slate-800/50">
                                {evidence.map(e => (
                                    <EvidenceRow key={e.id} evidence={e} />
                                ))}
                                {evidence.length === 0 && <EmptyState label="No direct evidence found" />}
                            </div>
                            {metrics && metrics.evidence > PAGE_SIZE && (
                                <PaginationControls
                                    currentPage={evidencePage}
                                    totalItems={metrics.evidence}
                                    pageSize={PAGE_SIZE}
                                    onPageChange={setEvidencePage}
                                />
                            )}
                        </div>
                    )}

                    {activeTab === 'filings' && (
                        <div>
                            <div className="divide-y divide-slate-800/50">
                                {documents.map(d => (
                                    <FilingRow key={d.document_id} filing={d} />
                                ))}
                                {documents.length === 0 && <EmptyState label="No SEC filings detected" />}
                            </div>
                            {metrics && metrics.filings > PAGE_SIZE && (
                                <PaginationControls
                                    currentPage={filingsPage}
                                    totalItems={metrics.filings}
                                    pageSize={PAGE_SIZE}
                                    onPageChange={setFilingsPage}
                                />
                            )}
                        </div>
                    )}

                    {activeTab === 'culture' && (
                        <div className="p-8 space-y-8">
                            {culture ? (
                                <>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                        <div className="space-y-6">
                                            <h3 className="text-xl font-black text-white flex items-center gap-2">
                                                <Activity className="text-blue-500" size={20} />
                                                Culture Intelligence
                                            </h3>
                                            <div className="grid grid-cols-2 gap-4">
                                                <CultureMetric label="Innovation" score={culture.innovation_score} />
                                                <CultureMetric label="AI Awareness" score={culture.ai_awareness_score} />
                                                <CultureMetric label="Data Driven" score={culture.data_driven_score} />
                                                <CultureMetric label="Change Readiness" score={culture.change_readiness_score} />
                                            </div>
                                            <div className="p-6 bg-blue-500/5 rounded-2xl border border-blue-500/10">
                                                <div className="flex justify-between items-end mb-4">
                                                    <div>
                                                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Overall Sentiment</div>
                                                        <div className="text-3xl font-black text-white">{(culture.overall_sentiment * 100).toFixed(1)}%</div>
                                                    </div>
                                                    <div className="text-right">
                                                        <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Rating</div>
                                                        <div className="text-2xl font-black text-blue-400">{culture.avg_rating.toFixed(1)} / 5.0</div>
                                                    </div>
                                                </div>
                                                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                                                    <div
                                                        className="bg-blue-500 h-full transition-all duration-1000"
                                                        style={{ width: `${culture.overall_sentiment * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-6">
                                            <h3 className="text-xl font-black text-white flex items-center gap-2">
                                                <Search className="text-purple-500" size={20} />
                                                Keyword Analysis
                                            </h3>
                                            <div className="space-y-4">
                                                <div>
                                                    <div className="text-[10px] font-black text-green-500 uppercase tracking-widest mb-2 flex items-center gap-1">
                                                        <Smile size={12} /> Positive Drivers
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        {culture.positive_keywords_found.map(kw => (
                                                            <span key={kw} className="px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-xs font-medium lowercase">
                                                                {kw}
                                                            </span>
                                                        ))}
                                                        {culture.positive_keywords_found.length === 0 && <span className="text-slate-600 text-xs italic">No positive keywords detected</span>}
                                                    </div>
                                                </div>
                                                <div>
                                                    <div className="text-[10px] font-black text-red-500 uppercase tracking-widest mb-2 flex items-center gap-1">
                                                        <Activity size={12} /> Friction Points
                                                    </div>
                                                    <div className="flex flex-wrap gap-2">
                                                        {culture.negative_keywords_found.map(kw => (
                                                            <span key={kw} className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-medium lowercase">
                                                                {kw}
                                                            </span>
                                                        ))}
                                                        {culture.negative_keywords_found.length === 0 && <span className="text-slate-600 text-xs italic">No negative keywords detected</span>}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-6 pt-8 border-t border-slate-800/50">
                                        <h3 className="text-xl font-black text-white flex items-center gap-2">
                                            <MessageSquare className="text-orange-500" size={20} />
                                            Employee Evidence
                                        </h3>
                                        <div className="grid grid-cols-1 gap-4">
                                            {gdReviews.map(r => (
                                                <ReviewRow key={r.id} review={r} />
                                            ))}
                                            {gdReviews.length === 0 && <EmptyState label="No employee reviews found" />}
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <EmptyState label="No workforce culture data available. Trigger collection in Playground." />
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function PaginationControls({ currentPage, totalItems, pageSize, onPageChange }: {
    currentPage: number;
    totalItems: number;
    pageSize: number;
    onPageChange: (page: number) => void
}) {
    const totalPages = Math.ceil(totalItems / pageSize);
    if (totalPages <= 1) return null;

    return (
        <div className="p-4 bg-[#18181b]/50 border-t border-slate-800 flex items-center justify-between">
            <div className="text-xs text-slate-500 font-medium">
                Showing <span className="text-slate-300">{(currentPage - 1) * pageSize + 1}</span> to <span className="text-slate-300">{Math.min(currentPage * pageSize, totalItems)}</span> of <span className="text-slate-300">{totalItems}</span>
            </div>
            <div className="flex gap-2">
                <button
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="px-3 py-1 bg-[#27272a] hover:bg-[#3f3f46] text-slate-300 rounded-md text-xs font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                    Previous
                </button>
                <div className="flex items-center px-3 text-xs font-bold text-blue-400 bg-blue-500/10 rounded-md border border-blue-500/20">
                    {currentPage} / {totalPages}
                </div>
                <button
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 bg-[#27272a] hover:bg-[#3f3f46] text-slate-300 rounded-md text-xs font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                    Next
                </button>
            </div>
        </div>
    );
}

function MiniStats({ label, value, icon, cardColor }: { label: string; value: string; icon: React.ReactNode, cardColor: string }) {
    const colors: any = {
        blue: 'text-blue-500 bg-blue-500/10',
        purple: 'text-purple-500 bg-purple-500/10',
        green: 'text-green-500 bg-green-500/10',
        orange: 'text-orange-500 bg-orange-500/10'
    };
    return (
        <div className="bg-[#0c0c0e] border border-slate-800 p-6 rounded-3xl shadow-xl flex items-center justify-between group hover:border-slate-700 transition-all">
            <div>
                <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">{label}</div>
                <div className="text-2xl font-black text-white">{value}</div>
            </div>
            <div className={`${colors[cardColor]} p-3 rounded-2xl group-hover:scale-110 transition-transform`}>{icon}</div>
        </div>
    );
}

function TabButton({ active, label, icon, onClick }: { active: boolean; label: string; icon: React.ReactNode; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold transition-all ${active ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20 scale-105' : 'text-slate-500 hover:text-slate-300'
                }`}
        >
            {icon}
            {label}
        </button>
    );
}

function SignalRow({ signal }: { signal: Signal }) {
    return (
        <div className="p-6 hover:bg-white/[0.01] transition-all grid grid-cols-1 md:grid-cols-4 items-center gap-6">
            <div className="md:col-span-2 space-y-2">
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-black px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 uppercase">
                        {signal.category.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{signal.source}</span>
                </div>
                <h4 className="font-bold text-slate-200">{signal.raw_value}</h4>
            </div>
            <div className="flex items-center gap-8">
                <div className="text-center">
                    <div className="text-[8px] font-black text-slate-600 uppercase mb-1">Score</div>
                    <div className="text-sm font-mono text-blue-400">{signal.normalized_score.toFixed(1)}</div>
                </div>
                <div className="text-center">
                    <div className="text-[8px] font-black text-slate-600 uppercase mb-1">Confidence</div>
                    <div className="text-sm font-mono text-slate-400">{(signal.confidence * 100).toFixed(0)}%</div>
                </div>
            </div>
            <div className="text-right text-xs text-slate-500 font-mono">
                {new Date(signal.signal_date).toLocaleDateString()}
            </div>
        </div>
    );
}

function EvidenceRow({ evidence }: { evidence: Evidence }) {
    return (
        <div className="p-6 hover:bg-white/[0.01] transition-all flex justify-between items-center">
            <div className="space-y-1">
                <div className="flex items-center gap-3">
                    <span className="text-[10px] font-black px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/20 uppercase">
                        {evidence.category.replace(/_/g, ' ')}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{evidence.source}</span>
                </div>
                <h4 className="font-bold text-slate-200">{evidence.title}</h4>
            </div>
            <div className="flex items-center gap-6">
                <span className="text-xs text-slate-500 font-mono">{new Date(evidence.evidence_date).toLocaleDateString()}</span>
                {evidence.url && (
                    <a href={evidence.url} target="_blank" rel="noreferrer" className="p-2 bg-slate-800 rounded-lg text-blue-400 hover:bg-slate-700">
                        <ExternalLink size={16} />
                    </a>
                )}
            </div>
        </div>
    );
}

function FilingRow({ filing }: { filing: Document }) {
    return (
        <div className="p-6 hover:bg-white/[0.01] transition-all flex justify-between items-center">
            <div className="flex items-center gap-6">
                <div className="w-12 h-12 bg-slate-800/50 rounded-2xl flex items-center justify-center text-orange-400">
                    <FileText size={24} />
                </div>
                <div>
                    <div className="flex items-center gap-3 mb-1">
                        <span className="text-[10px] font-black px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 uppercase">
                            {filing.filing_type}
                        </span>
                        <span className="text-[10px] text-green-400 font-bold uppercase tracking-widest flex items-center gap-1">
                            <ShieldCheck size={10} /> {filing.processing_status}
                        </span>
                    </div>
                    <h4 className="font-bold text-slate-200 font-mono text-sm">{filing.document_id}</h4>
                </div>
            </div>
            <div className="flex items-center gap-6">
                <div className="flex gap-2">
                    {filing.cik && (
                        <a
                            href={`https://www.sec.gov/cgi-bin/browse-edgar?CIK=${filing.cik}&action=getcompany`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 hover:bg-zinc-800 rounded-lg text-slate-400 hover:text-white transition-all"
                            title="View on SEC Edgar"
                        >
                            <ExternalLink size={16} />
                        </a>
                    )}
                    <Link
                        href={`/playground?path=/api/v1/documents/${filing.document_id}/chunks&run=true`}
                        className="p-2 bg-slate-800 rounded-lg text-slate-400 hover:bg-blue-600/20 hover:text-blue-400 transition-all"
                        title="Inspect Semantic Chunks"
                    >
                        <Search size={16} />
                    </Link>
                </div>
            </div>
        </div>
    );
}

function EmptyState({ label }: { label: string }) {
    return (
        <div className="p-20 text-center flex flex-col items-center gap-4 group">
            <div className="w-16 h-16 bg-slate-800/20 rounded-full flex items-center justify-center text-slate-700 group-hover:scale-110 transition-transform">
                <Search size={32} />
            </div>
            <p className="text-slate-500 text-sm font-medium italic">{label}</p>
        </div>
    );
}

function CultureMetric({ label, score }: { label: string, score: number }) {
    return (
        <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-2xl">
            <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">{label}</div>
            <div className="flex items-center gap-3">
                <div className="text-xl font-black text-white">{score.toFixed(1)}</div>
                <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                        className="bg-blue-500 h-full"
                        style={{ width: `${(score / 5) * 100}%` }}
                    />
                </div>
            </div>
        </div>
    );
}

function ReviewRow({ review }: { review: GlassdoorReview }) {
    return (
        <div className="p-6 bg-slate-900/30 border border-slate-800/50 rounded-2xl hover:border-slate-700 transition-all space-y-4">
            <div className="flex justify-between items-start">
                <div>
                    <h4 className="font-bold text-white text-lg leading-tight">{review.title}</h4>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-500 font-medium">
                        <span className="px-2 py-0.5 bg-slate-800 rounded text-slate-400">{review.job_title}</span>
                        <span>•</span>
                        <span>{new Date(review.review_date).toLocaleDateString()}</span>
                        <span>•</span>
                        <span className={review.is_current_employee ? "text-green-500" : "text-amber-500"}>
                            {review.is_current_employee ? "Current Employee" : "Former Employee"}
                        </span>
                    </div>
                </div>
                <div className="flex items-center gap-1 bg-blue-500/10 text-blue-400 px-3 py-1 rounded-full border border-blue-500/20">
                    <Smile size={14} />
                    <span className="font-black text-sm">{review.rating.toFixed(1)}</span>
                </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div className="space-y-1">
                    <div className="text-[10px] font-black text-green-500 uppercase tracking-widest">Pros</div>
                    <p className="text-slate-300 italic">"{review.pros}"</p>
                </div>
                <div className="space-y-1">
                    <div className="text-[10px] font-black text-red-500 uppercase tracking-widest">Cons</div>
                    <p className="text-slate-400 italic">"{review.cons}"</p>
                </div>
            </div>
        </div>
    );
}
