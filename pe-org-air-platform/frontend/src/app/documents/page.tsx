"use client";

import { useState, useEffect } from "react";
import { FileText, Download, Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface Company {
    company_id: string;
    ticker: string;
    name: string;
    sector: string;
    org_air: number;
}

type DocType = "ic-memo" | "lp-letter";

interface DownloadState {
    [key: string]: "idle" | "loading" | "done" | "error";
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function downloadDoc(companyId: string, docType: DocType, filename: string) {
    const res = await fetch(`${API_BASE}/api/v1/agent-ui/generate-${docType}/${companyId}`, {
        method: "POST",
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

export default function DocumentsPage() {
    const [companies, setCompanies] = useState<Company[]>([]);
    const [loading, setLoading] = useState(true);
    const [states, setStates] = useState<DownloadState>({});

    useEffect(() => {
        fetch(`${API_BASE}/api/v1/agent-ui/portfolio`)
            .then((r) => r.json())
            .then((data) => setCompanies(Array.isArray(data) ? data.filter((c: Company) => c.org_air > 0) : []))
            .catch(() => setCompanies([]))
            .finally(() => setLoading(false));
    }, []);

    const handleDownload = async (company: Company, docType: DocType) => {
        const key = `${company.company_id}-${docType}`;
        setStates((s) => ({ ...s, [key]: "loading" }));
        const filename =
            docType === "ic-memo"
                ? `IC_Memo_${company.ticker}.docx`
                : `LP_Letter_${company.ticker}.docx`;
        try {
            await downloadDoc(company.company_id, docType, filename);
            setStates((s) => ({ ...s, [key]: "done" }));
            setTimeout(() => setStates((s) => ({ ...s, [key]: "idle" })), 3000);
        } catch {
            setStates((s) => ({ ...s, [key]: "error" }));
            setTimeout(() => setStates((s) => ({ ...s, [key]: "idle" })), 4000);
        }
    };

    const btnState = (companyId: string, docType: DocType) =>
        states[`${companyId}-${docType}`] ?? "idle";

    const DocButton = ({
        company,
        docType,
        label,
    }: {
        company: Company;
        docType: DocType;
        label: string;
    }) => {
        const state = btnState(company.company_id, docType);
        const isLoading = state === "loading";
        return (
            <button
                onClick={() => handleDownload(company, docType)}
                disabled={isLoading}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
                    ${state === "done" ? "bg-green-600/20 text-green-400 border border-green-600/30" :
                      state === "error" ? "bg-red-600/20 text-red-400 border border-red-600/30" :
                      "bg-blue-600/20 text-blue-400 border border-blue-600/30 hover:bg-blue-600/30"}
                    disabled:opacity-60`}
            >
                {state === "loading" && <Loader2 size={14} className="animate-spin" />}
                {state === "done" && <CheckCircle2 size={14} />}
                {state === "error" && <AlertCircle size={14} />}
                {state === "idle" && <Download size={14} />}
                {state === "loading" ? "Generating…" :
                 state === "done" ? "Downloaded" :
                 state === "error" ? "Failed" : label}
            </button>
        );
    };

    return (
        <div className="p-8 max-w-5xl mx-auto">
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                    <FileText className="text-blue-400" size={28} />
                    <h1 className="text-2xl font-bold">Document Generator</h1>
                </div>
                <p className="text-slate-400 text-sm">
                    Generate IC Memos and LP Letters for portfolio companies. Downloads a Word (.docx) file.
                </p>
            </div>

            {loading ? (
                <div className="flex items-center gap-3 text-slate-400">
                    <Loader2 size={20} className="animate-spin" />
                    <span>Loading portfolio…</span>
                </div>
            ) : companies.length === 0 ? (
                <div className="text-slate-500 text-sm">No portfolio companies found.</div>
            ) : (
                <div className="space-y-3">
                    {companies.map((company) => (
                        <div
                            key={company.company_id}
                            className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl px-6 py-4"
                        >
                            <div className="flex items-center gap-4">
                                <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center">
                                    <span className="text-xs font-bold text-blue-400">{company.ticker}</span>
                                </div>
                                <div>
                                    <div className="font-medium text-slate-100">{company.name}</div>
                                    <div className="text-xs text-slate-500 capitalize">
                                        {company.sector} · Org-AI-R {company.org_air > 0 ? company.org_air.toFixed(1) : "N/A"}
                                    </div>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <DocButton company={company} docType="ic-memo" label="IC Memo" />
                                <DocButton company={company} docType="lp-letter" label="LP Letter" />
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <div className="mt-8 p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-500">
                <strong className="text-slate-400">Note:</strong> Generation runs the full due diligence workflow and may take 15–30 seconds.
                The file downloads automatically when ready.
            </div>
        </div>
    );
}
