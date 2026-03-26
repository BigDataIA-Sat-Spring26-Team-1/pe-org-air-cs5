"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
    Terminal,
    ChevronRight,
    Loader2,
    FileJson,
    Send,
    Database,
    Shield,
    Activity,
    Globe,
    Search,
    Brain,
    FileText,
    Settings,
    ChevronDown,
    TestTube,
    Plus,
    Trash2,
    AlertCircle,
    Info,
    Users
} from "lucide-react";

interface ParamDef {
    name: string;
    type: 'string' | 'number' | 'boolean';
    required: boolean;
    description?: string;
    default?: any;
    options?: string[];
}

interface Endpoint {
    name: string;
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
    path: string;
    description: string;
    body?: any;
    tag: string;
    queryParams?: ParamDef[];
}

interface Category {
    name: string;
    tag: string;
    icon: React.ReactNode;
    endpoints: Endpoint[];
}

const CATEGORIES: Category[] = [
    {
        name: "Companies",
        tag: "Companies",
        icon: <Database size={16} />,
        endpoints: [
            { tag: "Companies", name: "List Companies", method: 'GET', path: '/api/v1/companies/', description: "Get tracked targets", queryParams: [{ name: 'limit', type: 'number', required: false, default: 50 }, { name: 'offset', type: 'number', required: false, default: 0 }] },
            { tag: "Companies", name: "Get Company", method: 'GET', path: '/api/v1/companies/{company_id}', description: "Retrieve single company details" },
            { tag: "Companies", name: "Create Company", method: 'POST', path: '/api/v1/companies/', description: "Register a new target", body: { name: "Example Inc.", ticker: "EXMP", industry_id: "550e8400-e29b-41d4-a716-446655440000", position_factor: 0.5 } },
            { tag: "Companies", name: "Update Company", method: 'PUT', path: '/api/v1/companies/{company_id}', description: "Update company details", body: { name: "Updated Inc.", ticker: "UPDT" } },
            { tag: "Companies", name: "Delete Company", method: 'DELETE', path: '/api/v1/companies/{company_id}', description: "Remove from portfolio" },
            { tag: "Companies", name: "Get Company Signals", method: 'GET', path: '/api/v1/companies/{company_id}/signals/{category}', description: "Get signals by category" },
            { tag: "Companies", name: "Get Company Evidence", method: 'GET', path: '/api/v1/companies/{company_id}/evidence', description: "Get company evidence" },
        ]
    },
    {
        name: "Documents (SEC)",
        tag: "Documents",
        icon: <FileText size={16} />,
        endpoints: [
            { tag: "Documents", name: "Collect Filings", method: 'POST', path: '/api/v1/documents/collect', description: "Trigger SEC scraper", body: { tickers: ["CAT"], limit: 2 } },
            { tag: "Documents", name: "Deploy Airflow DAG", method: 'POST', path: '/api/v1/documents/collect-airflow', description: "Trigger SEC Airflow DAG", body: { tickers: ["CAT"], limit: 2 } },
            {
                tag: "Documents",
                name: "Search Documents",
                method: 'GET',
                path: '/api/v1/documents',
                description: "Filter filings by ticker/type",
                queryParams: [
                    { name: "company", type: "string", required: false, description: "Filter by ticker/name" },
                    { name: "filing_type", type: "string", required: false, description: "e.g. 10-K", options: ["10-K", "10-Q", "8-K", "DEF 14A"] },
                    { name: "limit", type: "number", required: false, default: 50, description: "Max records to return" },
                    { name: "offset", type: "number", required: false, default: 0 }
                ]
            },
            { tag: "Documents", name: "Get Document", method: 'GET', path: '/api/v1/documents/{document_id}', description: "Retrieve filing metadata" },
            {
                tag: "Documents",
                name: "Inspect Chunks",
                method: 'GET',
                path: '/api/v1/documents/{document_id}/chunks',
                description: "View semantic segments",
                queryParams: [
                    { name: "section", type: "string", required: false, description: "Filter by section name" },
                    { name: "limit", type: "number", required: false, default: 200 },
                    { name: "offset", type: "number", required: false, default: 0 }
                ]
            },
        ]
    },
    {
        name: "External Signals",
        tag: "Signals",
        icon: <Activity size={16} />,
        endpoints: [
            { tag: "Signals", name: "Collect Signals", method: 'POST', path: '/api/v1/signals/collect', description: "Collect signals", body: { company_id: "uuid-here", categories: ["jobs", "patents"] } },
            { tag: "Signals", name: "List Signals", method: 'GET', path: '/api/v1/signals/', description: "Retrieve all captured signals" },
            { tag: "Signals", name: "List Evidence", method: 'GET', path: '/api/v1/signals/evidence', description: "Supporting links/docs" },
            { tag: "Signals", name: "Get Company Summary", method: 'GET', path: '/api/v1/signals/summary', description: "Get company summary" },
            { tag: "Signals", name: "Get Signals by Category", method: 'GET', path: '/api/v1/signals/details/{category}', description: "Get signals by category" },
        ]
    },
    {
        name: "Culture & Glassdoor",
        tag: "Culture",
        icon: <Users size={16} />,
        endpoints: [
            { tag: "Culture", name: "Collect Glassdoor Reviews", method: 'POST', path: '/api/v1/signals/collect/glassdoor', description: "Trigger Glassdoor sentiment analysis", queryParams: [{ name: 'ticker', type: 'string', required: true }, { name: 'limit', type: 'number', required: false, default: 20 }] },
            { tag: "Culture", name: "Get Culture Scores", method: 'GET', path: '/api/v1/signals/culture/{ticker}', description: "Retrieve aggregated sentiment metrics" },
            { tag: "Culture", name: "Get Glassdoor Evidence", method: 'GET', path: '/api/v1/signals/culture/reviews/{ticker}', description: "View raw employee pros/cons", queryParams: [{ name: 'limit', type: 'number', required: false, default: 50 }, { name: 'offset', type: 'number', required: false, default: 0 }] },
        ]
    },
    {
        name: "Evidence",
        tag: "Evidence",
        icon: <Shield size={16} />,
        endpoints: [
            { tag: "Evidence", name: "Run Backfill", method: 'POST', path: '/api/v1/evidence/backfill', description: "Force refresh evidence" },
            { tag: "Evidence", name: "Get Backfill Stats", method: 'GET', path: '/api/v1/evidence/stats', description: "Get backfill stats" },
        ]
    },
    {
        name: "Analytical Integration",
        tag: "Integration",
        icon: <Brain size={16} />,
        endpoints: [
            {
                tag: "Integration",
                name: "Run Integration Pipeline",
                method: 'POST',
                path: '/api/v1/integration/run',
                description: "Force real-time deep scoring for one or more tickers (Board + SEC + Talent + Culture)",
                body: {
                    tickers: ["NVDA", "JPM", "GE"]
                }
            },
            {
                tag: "Integration",
                name: "Deploy Airflow DAG",
                method: 'POST',
                path: '/api/v1/integration/run-airflow',
                description: "Trigger the Airflow Integration Pipeline DAG",
                body: {
                    tickers: ["NVDA", "JPM", "GE"]
                }
            },
        ]
    },
    {
        name: "Assessments",
        tag: "Assessments",
        icon: <Brain size={16} />,
        endpoints: [
            { tag: "Assessments", name: "Create Assessment", method: 'POST', path: '/api/v1/assessments', description: "Create assessment", body: { company_id: "uuid-here", assessment_type: "due_diligence", primary_assessor: "Jane Doe" } },
            { tag: "Assessments", name: "List Assessments", method: 'GET', path: '/api/v1/assessments', description: "List assessments" },
            { tag: "Assessments", name: "Get Assessment", method: 'GET', path: '/api/v1/assessments/{assessment_id}', description: "Get assessment" },
            { tag: "Assessments", name: "Update Assessment Status", method: 'PATCH', path: '/api/v1/assessments/{assessment_id}/status', description: "Update assessment status", body: { status: "in_progress" } },
            { tag: "Assessments", name: "Add Dimension Score", method: 'POST', path: '/api/v1/assessments/{assessment_id}/scores', description: "Add dimension score", body: { assessment_id: "uuid-here", dimension: "data_infrastructure", score: 75, confidence: 0.85 } },
            { tag: "Assessments", name: "Get Dimension Scores", method: 'GET', path: '/api/v1/assessments/{assessment_id}/scores', description: "Get dimension scores" },
            { tag: "Assessments", name: "Update Dimension Score", method: 'PUT', path: '/api/v1/scores/{score_id}', description: "Update dimension score", body: { score: 80, confidence: 0.9 } },
        ]
    },
    {
        name: "Metrics",
        tag: "Metrics",
        icon: <Globe size={16} />,
        endpoints: [
            { tag: "Metrics", name: "Industry Distribution", method: 'GET', path: '/api/v1/metrics/industry-distribution', description: "Get industry distribution" },
            { tag: "Metrics", name: "Company Stats", method: 'GET', path: '/api/v1/metrics/company-stats', description: "Get company stats" },
            { tag: "Metrics", name: "Signal Distribution", method: 'GET', path: '/api/v1/metrics/signal-distribution', description: "Get signal distribution" },
            { tag: "Metrics", name: "Global Summary", method: 'GET', path: '/api/v1/metrics/summary', description: "Get global summary metrics" },
        ]
    },
    {
        name: "Configuration",
        tag: "Configuration",
        icon: <Settings size={16} />,
        endpoints: [
            { tag: "Configuration", name: "Get Config Vars", method: 'GET', path: '/api/v1/config/vars', description: "Get config vars" },
            { tag: "Configuration", name: "Get Dimension Weights", method: 'GET', path: '/api/v1/config/dimension-weights', description: "Get dimension weights" },
        ]
    },
    {
        name: "RAG & AI Kernel",
        tag: "RAG",
        icon: <Brain size={16} />,
        endpoints: [
            {
                tag: "RAG",
                name: "Ingest Company Data",
                method: 'POST',
                path: '/api/v1/rag/ingest',
                description: "Pull Snowflake data into Vector Store",
                queryParams: [{ name: 'ticker', type: 'string', required: true, description: "Ticker to ingest (e.g. NVDA)" }]
            },
            {
                tag: "RAG",
                name: "RAG Deep Query",
                method: 'POST',
                path: '/api/v1/rag/query',
                description: "AI retrieval with HyDE, RRF Fusion, and Filters",
                body: { ticker: "NVDA", query: "What are the core AI initiatives?", use_hyde: true, top_k: 5, dimension: "data_infrastructure", min_confidence: 0.5 }
            },
            {
                tag: "RAG",
                name: "Generated IC Justification",
                method: 'POST',
                path: '/api/v1/rag/justify',
                description: "Produce full IC package with LLM justifications",
                body: { ticker: "NVDA", top_k: 5 }
            },
            {
                tag: "RAG",
                name: "Ingest Analyst Note",
                method: 'POST',
                path: '/api/v1/rag/notes/ingest',
                description: "Add manual DD notes (interview, data-room, etc)",
                body: {
                    ticker: "NVDA",
                    note: {
                        title: "CTO Interview",
                        note_type: "interview",
                        content: "The company is transitioning all workloads to H100 clusters.",
                        analyst_name: "Aakash",
                        tags: ["strategy", "compute"]
                    }
                }
            },
            {
                tag: "RAG",
                name: "List Analyst Notes",
                method: 'GET',
                path: '/api/v1/rag/notes/{ticker}',
                description: "View manual notes indexed for ticker"
            },
            {
                tag: "RAG",
                name: "Trigger Indexing DAG",
                method: 'POST',
                path: '/api/v1/rag/index-airflow',
                description: "Trigger Airflow 'pe_evidence_indexing' DAG"
            },
            {
                tag: "RAG",
                name: "Complete Analysis Pipeline",
                method: 'POST',
                path: '/api/v1/rag/complete-pipeline',
                description: "Run end-to-end analysis (CS1 -> CS3 -> CS2 -> IC Justify)",
                queryParams: [
                    { name: "ticker", type: "string", required: true, description: "Ticker (e.g. NVDA)" },
                    { name: "dimension", type: "string", required: false, default: "data_infrastructure", options: ["data_infrastructure", "ai_governance", "technology_stack", "talent", "leadership", "use_case_portfolio", "culture"] }
                ]
            },
            { tag: "RAG", name: "RAG Health", method: 'GET', path: '/api/v1/rag/health', description: "Check status of RAG infra" },
        ]
    },
    {
        name: "Industries",
        tag: "Industries",
        icon: <Database size={16} />,
        endpoints: [
            { tag: "Industries", name: "List Industries", method: 'GET', path: '/api/v1/industries/', description: "List industries" },
        ]
    },
    {
        name: "Testing",
        tag: "Testing",
        icon: <TestTube size={16} />,
        endpoints: [
            { tag: "Testing", name: "Run System Tests", method: 'POST', path: '/api/v1/system/run-tests', description: "Trigger full pytest infrastructure audit" },
        ]
    },
    {
        name: "System",
        tag: "Health",
        icon: <Settings size={16} />,
        endpoints: [
            { tag: "Health", name: "Health Check", method: 'GET', path: '/health', description: "Service status monitoring" },
        ]
    },
    {
        name: "Agentic Workflow (CS5)",
        tag: "AgentUI",
        icon: <Brain size={16} />,
        endpoints: [
            {
                tag: "AgentUI",
                name: "Portfolio Dashboard",
                method: 'GET',
                path: '/api/v1/agent-ui/portfolio',
                description: "Fetch live portfolio data — all companies with Org-AI-R, V^R, H^R scores",
                queryParams: [{ name: "fund_id", type: "string", required: false, default: "growth_fund_v", description: "Fund identifier" }],
            },
            {
                tag: "AgentUI",
                name: "Fund-AI-R Score",
                method: 'GET',
                path: '/api/v1/agent-ui/fund-air',
                description: "EV-weighted Fund-AI-R metric across the whole portfolio",
                queryParams: [{ name: "fund_id", type: "string", required: false, default: "growth_fund_v", description: "Fund identifier" }],
            },
            {
                tag: "AgentUI",
                name: "Trigger Due Diligence",
                method: 'POST',
                path: '/api/v1/agent-ui/trigger-due-diligence',
                description: "Run the full LangGraph agentic workflow: SEC → Scoring → Evidence → Value Creation. HITL gate fires when score is outside [40, 85] or EBITDA impact > 5%.",
                body: {
                    company_id: "NVDA",
                    assessment_type: "full",
                    requested_by: "analyst",
                    target_org_air: 75.0,
                },
            },
            {
                tag: "AgentUI",
                name: "Assessment History",
                method: 'GET',
                path: '/api/v1/agent-ui/history/{company_id}',
                description: "Retrieve prior due diligence runs for a company (uses CS3 + Snowflake persistence)",
            },
        ],
    },
    {
        name: "MCP Tools (CS5)",
        tag: "MCPTools",
        icon: <Terminal size={16} />,
        endpoints: [
            {
                tag: "MCPTools",
                name: "MCP Health",
                method: 'GET',
                path: '/mcp/health',
                description: "Liveness check for the MCP server (SSE transport, port 3001)",
            },
            {
                tag: "MCPTools",
                name: "Portfolio Summary Tool",
                method: 'POST',
                path: '/mcp/tools/get_portfolio_summary',
                description: "MCP tool: fetch all portfolio companies with scores from CS1–CS3",
                body: { fund_id: "growth_fund_v" },
            },
            {
                tag: "MCPTools",
                name: "Calculate Org-AI-R Tool",
                method: 'POST',
                path: '/mcp/tools/calculate_org_air_score',
                description: "MCP tool: pull the latest Org-AI-R, V^R and H^R scores for a company from CS3",
                body: { company_id: "NVDA" },
            },
            {
                tag: "MCPTools",
                name: "Company Evidence Tool",
                method: 'POST',
                path: '/mcp/tools/get_company_evidence',
                description: "MCP tool: fetch granular evidence signals (patents, SEC filings, job posts) from CS2",
                body: { company_id: "NVDA" },
            },
            {
                tag: "MCPTools",
                name: "Generate Justification Tool",
                method: 'POST',
                path: '/mcp/tools/generate_justification',
                description: "MCP tool: CS4 RAG-powered justification for a single Org-AI-R dimension",
                body: { company_id: "NVDA", dimension: "data_infrastructure" },
            },
            {
                tag: "MCPTools",
                name: "Project EBITDA Impact Tool",
                method: 'POST',
                path: '/mcp/tools/project_ebitda_impact',
                description: "MCP tool: v2.0 gamma-parameter EBITDA projection across base, conservative and optimistic scenarios",
                body: { company_id: "NVDA", entry_score: 45, target_score: 75, h_r_score: 60 },
            },
            {
                tag: "MCPTools",
                name: "Gap Analysis Tool",
                method: 'POST',
                path: '/mcp/tools/run_gap_analysis',
                description: "MCP tool: dimension-level gap analysis with prioritised 100-day initiatives",
                body: { company_id: "NVDA", target_org_air: 75 },
            },
        ],
    },
];

const ALL_ENDPOINTS: any[] = CATEGORIES.flatMap(c => c.endpoints);

export default function Playground() {
    const [selectedEndpoint, setSelectedEndpoint] = useState<Endpoint>(ALL_ENDPOINTS[0]);
    const [pathParams, setPathParams] = useState<Record<string, string>>({});

    // Schema-defined query params values
    const [paramValues, setParamValues] = useState<Record<string, any>>({});

    // Custom/Extra query params
    const [extraQueryParams, setExtraQueryParams] = useState<{ key: string, value: string }[]>([]);

    const [requestBody, setRequestBody] = useState<string>("");
    const [response, setResponse] = useState<any>(null);
    const [status, setStatus] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [viewMode, setViewMode] = useState<'json' | 'table'>('json');
    const [expandedTags, setExpandedTags] = useState<string[]>(["Companies", "Documents"]);
    const [validationError, setValidationError] = useState<string | null>(null);

    const API_BASE = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) || "";

    // Initialize state when endpoint changes
    useEffect(() => {
        // Path Params
        const matches = selectedEndpoint.path.match(/{([^}]+)}/g);
        const newPathParams: Record<string, string> = {};
        if (matches) {
            matches.forEach((m: string) => {
                const key = m.replace(/{|}/g, '');
                newPathParams[key] = "";
            });
        }
        setPathParams(newPathParams);

        // Query Params Defaults
        const newParamValues: Record<string, any> = {};
        if (selectedEndpoint.queryParams) {
            selectedEndpoint.queryParams.forEach((p: ParamDef) => {
                if (p.default !== undefined) {
                    newParamValues[p.name] = p.default;
                } else {
                    newParamValues[p.name] = "";
                }
            });
        }
        setParamValues(newParamValues);

        setExtraQueryParams([]);
        setRequestBody(selectedEndpoint.body ? JSON.stringify(selectedEndpoint.body, null, 2) : "");
        setResponse(null);
        setStatus(null);
        setValidationError(null);
    }, [selectedEndpoint]);

    const toggleTag = (tag: string) => {
        setExpandedTags((prev: string[]) => prev.includes(tag) ? prev.filter((t: string) => t !== tag) : [...prev, tag]);
    };

    const handleRun = async () => {
        setLoading(true);
        setResponse(null);
        setStatus(null);
        setValidationError(null);

        // Validation
        // Check Path Params
        for (const [key, val] of Object.entries(pathParams)) {
            if (!val || val.trim() === "") {
                setValidationError(`Path variable {${key}} is required.`);
                setLoading(false);
                return;
            }
        }

        // Check Required Query Params
        if (selectedEndpoint.queryParams) {
            for (const p of selectedEndpoint.queryParams) {
                if (p.required) {
                    const val = paramValues[p.name];
                    if (val === undefined || val === "" || val === null) {
                        setValidationError(`Query parameter '${p.name}' is required.`);
                        setLoading(false);
                        return;
                    }
                }
            }
        }

        // Build URL
        let finalPath = selectedEndpoint.path;
        Object.entries(pathParams).forEach(([key, value]) => {
            finalPath = finalPath.replace(`{${key}}`, value);
        });

        // Append query params
        const qs = new URLSearchParams();

        // Add schema params
        Object.entries(paramValues).forEach(([key, value]) => {
            if (value !== undefined && value !== "" && value !== null) {
                qs.append(key, String(value));
            }
        });

        // Add extra params
        extraQueryParams.filter((p: { key: string, value: string }) => p.key && p.value).forEach((p: { key: string, value: string }) => {
            qs.append(p.key, p.value);
        });

        if (qs.toString()) {
            finalPath += `?${qs.toString()}`;
        }

        try {
            const options: RequestInit = {
                method: selectedEndpoint.method,
                headers: { "Content-Type": "application/json" },
            };

            if (selectedEndpoint.method !== 'GET' && requestBody) {
                try {
                    options.body = requestBody;
                } catch (e) {
                    setResponse({ error: "Invalid JSON in request body" });
                    setLoading(false);
                    return;
                }
            }

            const res = await fetch(`${API_BASE}${finalPath}`, options);
            setStatus(res.status);

            let data;
            if (res.status === 204) {
                data = { message: "Company Deleted" };
            } else {
                const text = await res.text();
                try {
                    data = text ? JSON.parse(text) : { message: "Success" };
                } catch (e) {
                    data = { message: "Response received but could not be parsed as JSON", raw: text };
                }
            }
            setResponse(data);
        } catch (err) {
            setResponse({ error: "Request failed", details: String(err) });
        } finally {
            setLoading(false);
        }
    };

    const addExtraQueryParam = () => {
        setExtraQueryParams([...extraQueryParams, { key: "", value: "" }]);
    };

    const updateExtraQueryParam = (index: number, field: 'key' | 'value', val: string) => {
        const newParams = [...extraQueryParams];
        newParams[index][field] = val;
        setExtraQueryParams(newParams);
    };

    const removeExtraQueryParam = (index: number) => {
        setExtraQueryParams(extraQueryParams.filter((_: any, i: number) => i !== index));
    };

    // Construct preview URL
    const previewUrl = useMemo(() => {
        let url = selectedEndpoint.path;
        Object.entries(pathParams).forEach(([key, value]) => {
            url = url.replace(`{${key}}`, value || `{${key}}`);
        });

        const qs = new URLSearchParams();
        Object.entries(paramValues).forEach(([key, value]) => {
            if (value !== undefined && value !== "" && value !== null) {
                qs.append(key, String(value));
            }
        });
        extraQueryParams.filter(p => p.key && p.value).forEach(p => {
            qs.append(p.key, p.value);
        });

        if (qs.toString()) {
            url += `?${qs.toString()}`;
        }
        return url;
    }, [selectedEndpoint, pathParams, paramValues, extraQueryParams]);

    return (
        <div className="flex flex-col lg:flex-row min-h-screen bg-[#09090b] text-slate-300">
            {/* Sidebar */}
            <div className="w-full lg:w-80 border-r border-slate-800 flex flex-col h-screen overflow-hidden">
                <div className="p-6 border-b border-slate-800 shrink-0">
                    <div className="flex items-center gap-2 mb-1">
                        <div className="w-6 h-6 bg-blue-600 rounded-lg flex items-center justify-center">
                            <Terminal size={14} className="text-white" />
                        </div>
                        <h1 className="font-black text-white tracking-tighter">ORG-AI-R API</h1>
                    </div>
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Unified Intelligence Sandbox</p>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-hide">
                    {CATEGORIES.map(cat => (
                        <div key={cat.tag} className="space-y-1">
                            <button
                                onClick={() => toggleTag(cat.tag)}
                                className="w-full flex items-center justify-between p-2 hover:bg-white/[0.02] rounded-lg transition-all group"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="text-slate-500 group-hover:text-blue-400 transition-colors">{cat.icon}</span>
                                    <span className="text-xs font-bold text-slate-400 group-hover:text-slate-200 uppercase tracking-wider">{cat.name}</span>
                                </div>
                                <ChevronDown size={14} className={`text-slate-600 transition-transform ${expandedTags.includes(cat.tag) ? "" : "-rotate-90"}`} />
                            </button>

                            {expandedTags.includes(cat.tag) && (
                                <div className="space-y-1 pl-4 animate-in slide-in-from-top-1 duration-200">
                                    {cat.endpoints.map((ep: Endpoint) => (
                                        <button
                                            key={ep.name}
                                            onClick={() => setSelectedEndpoint(ep)}
                                            className={`w-full text-left p-2.5 rounded-xl transition-all group relative ${selectedEndpoint.path === ep.path && selectedEndpoint.name === ep.name
                                                ? "bg-blue-600/10 text-blue-400"
                                                : "hover:bg-white/[0.01] text-slate-500 hover:text-slate-300"
                                                }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className={`text-[8px] font-black w-7 text-center ${ep.method === 'GET' ? 'text-green-500' : 'text-blue-500'
                                                    }`}>{ep.method}</span>
                                                <span className="text-[11px] font-medium truncate">{ep.name}</span>
                                            </div>
                                            {selectedEndpoint.path === ep.path && selectedEndpoint.name === ep.name && (
                                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-blue-500 rounded-full" />
                                            )}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 h-screen overflow-y-auto p-8 lg:p-12 space-y-8">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <div className="flex items-center gap-3 text-blue-400 mb-2">
                            <div className="h-0.5 w-8 bg-blue-500/30 rounded-full" />
                            <span className="text-xs font-black uppercase tracking-widest">{selectedEndpoint.tag}</span>
                        </div>
                        <h2 className="text-3xl font-black text-white tracking-tight">{selectedEndpoint.name}</h2>
                        <p className="text-slate-500 text-sm mt-1">{selectedEndpoint.description}</p>
                    </div>
                </div>

                <div className="flex flex-col gap-8">
                    {/* Input Panel */}
                    <div className="space-y-6">
                        <div className="bg-[#0c0c0e]/50 border border-slate-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden group">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/5 blur-[100px] -mr-32 -mt-32 rounded-full" />

                            <div className="space-y-6 relative z-10">

                                {validationError && (
                                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3 text-red-400 animate-in fade-in slide-in-from-top-2">
                                        <AlertCircle size={16} />
                                        <span className="text-xs font-bold">{validationError}</span>
                                    </div>
                                )}

                                <div className="space-y-3">
                                    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                        <Globe size={12} className="text-blue-500" /> Endpoint Path
                                    </label>
                                    <div className="flex flex-col md:flex-row gap-3">
                                        <div className="flex-1 bg-black/40 border border-slate-800 rounded-2xl py-4 px-6 text-sm font-mono text-blue-400 flex items-center break-all">
                                            {previewUrl}
                                        </div>
                                        <button
                                            onClick={handleRun}
                                            disabled={loading}
                                            className="bg-blue-600 hover:bg-blue-500 active:scale-95 disabled:bg-blue-900/50 disabled:text-slate-500 text-white px-8 py-4 rounded-2xl font-black text-xs tracking-widest flex items-center justify-center gap-2 transition-all shadow-[0_0_30px_rgba(37,99,235,0.2)]"
                                        >
                                            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                                            RUN
                                        </button>
                                    </div>
                                </div>

                                {/* Path Params Inputs */}
                                {Object.keys(pathParams).length > 0 && (
                                    <div className="space-y-3 animate-in fade-in duration-500">
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                            <Settings size={12} className="text-orange-500" /> Path Variables <span className="text-red-400">*</span>
                                        </label>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {Object.keys(pathParams).map(key => (
                                                <div key={key} className="flex flex-col gap-1">
                                                    <span className="text-[10px] font-bold text-slate-400 ml-1">{key}</span>
                                                    <input
                                                        type="text"
                                                        placeholder={`Required value for ${key}`}
                                                        value={pathParams[key]}
                                                        onChange={(e) => setPathParams({ ...pathParams, [key]: e.target.value })}
                                                        className="bg-black/40 border border-slate-800 rounded-xl py-3 px-4 text-xs font-mono text-white focus:outline-none focus:border-blue-500/50"
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Defined Query Params */}
                                {selectedEndpoint.queryParams && selectedEndpoint.queryParams.length > 0 && (
                                    <div className="space-y-3 animate-in fade-in duration-500">
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-2">
                                            <Search size={12} className="text-green-500" /> Parameters
                                        </label>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            {selectedEndpoint.queryParams.map(param => (
                                                <div key={param.name} className="flex flex-col gap-1 group">
                                                    <div className="flex items-center justify-between ml-1">
                                                        <span className="text-[10px] font-bold text-slate-400 group-hover:text-blue-400 transition-colors">
                                                            {param.name} {param.required && <span className="text-red-500">*</span>}
                                                        </span>
                                                        <span className="text-[9px] text-slate-600 font-mono">
                                                            {param.type} {param.required ? '(required)' : '(optional)'}
                                                        </span>
                                                    </div>

                                                    {param.options ? (
                                                        <select
                                                            value={paramValues[param.name] || ""}
                                                            onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                                                            className="bg-black/40 border border-slate-800 rounded-xl py-3 px-4 text-xs font-mono text-slate-300 focus:outline-none focus:border-blue-500/50 appearance-none"
                                                        >
                                                            <option value="">(any)</option>
                                                            {param.options.map(opt => (
                                                                <option key={opt} value={opt}>{opt}</option>
                                                            ))}
                                                        </select>
                                                    ) : (
                                                        <input
                                                            type={param.type === 'number' ? 'number' : 'text'}
                                                            placeholder={param.description || (param.default ? `Default: ${param.default}` : `Value for ${param.name}`)}
                                                            value={paramValues[param.name] === undefined ? "" : paramValues[param.name]}
                                                            onChange={(e) => setParamValues({ ...paramValues, [param.name]: e.target.value })}
                                                            className={`bg-black/40 border border-slate-800 rounded-xl py-3 px-4 text-xs font-mono text-slate-300 focus:outline-none focus:border-blue-500/50 ${param.required && !paramValues[param.name] ? 'border-red-900/50' : ''
                                                                }`}
                                                        />
                                                    )}
                                                    {param.description && (
                                                        <span className="text-[9px] text-slate-600 ml-1">{param.description}</span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Extra Query Params Inputs */}
                                <div className="space-y-3 border-t border-slate-800/50 pt-4">
                                    <div className="flex items-center justify-between">
                                        <label className="text-[10px] font-black text-slate-600 uppercase tracking-widest flex items-center gap-2">
                                            <Plus size={10} /> Additional Parameters
                                        </label>
                                        <button onClick={addExtraQueryParam} className="text-[10px] font-bold text-slate-500 hover:text-white flex items-center gap-1 transition-colors">
                                            + ADD CUSTOM
                                        </button>
                                    </div>

                                    {extraQueryParams.length > 0 && (
                                        <div className="space-y-2">
                                            {extraQueryParams.map((param, idx) => (
                                                <div key={idx} className="flex items-center gap-2 animate-in slide-in-from-left-2 duration-200">
                                                    <input
                                                        type="text"
                                                        placeholder="Key"
                                                        value={param.key}
                                                        onChange={(e) => updateExtraQueryParam(idx, 'key', e.target.value)}
                                                        className="flex-1 bg-black/40 border border-slate-800 rounded-xl py-2 px-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-blue-500/50"
                                                    />
                                                    <input
                                                        type="text"
                                                        placeholder="Value"
                                                        value={param.value}
                                                        onChange={(e) => updateExtraQueryParam(idx, 'value', e.target.value)}
                                                        className="flex-1 bg-black/40 border border-slate-800 rounded-xl py-2 px-3 text-xs font-mono text-slate-300 focus:outline-none focus:border-blue-500/50"
                                                    />
                                                    <button onClick={() => removeExtraQueryParam(idx)} className="p-2 hover:bg-red-500/10 rounded-lg text-slate-600 hover:text-red-400 transition-colors">
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>

                                {selectedEndpoint.method !== 'GET' && (
                                    <div className="space-y-3 animate-in fade-in duration-500">
                                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <FileJson size={12} className="text-purple-500" /> Request Payload
                                            </div>
                                            <span className="text-[9px] text-slate-700">application/json</span>
                                        </label>
                                        <div className="bg-black/40 rounded-2xl border border-slate-800 p-1">
                                            <textarea
                                                value={requestBody}
                                                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setRequestBody(e.target.value)}
                                                rows={10}
                                                className="w-full bg-transparent p-6 text-xs font-mono text-slate-400 focus:outline-none resize-none scrollbar-hide"
                                                placeholder="{ ... }"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Output Panel */}
                    <div className="w-full">
                        <div className="bg-[#0c0c0e]/50 border border-slate-800 rounded-3xl min-h-[500px] flex flex-col overflow-hidden shadow-2xl relative">
                            <div className="absolute top-0 right-0 w-96 h-96 bg-green-500/5 blur-[120px] -mr-48 -mt-48 rounded-full" />

                            <div className="p-8 border-b border-slate-800 flex items-center justify-between shrink-0 relative z-10">
                                <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-2">
                                        <Activity size={14} className="text-slate-500" />
                                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Execution Result</h3>
                                    </div>
                                    {status && (
                                        <span className={`text-[9px] font-bold px-2.5 py-1 rounded-md border ${status < 300
                                            ? 'bg-green-500/10 border-green-500/20 text-green-400'
                                            : 'bg-red-500/10 border-red-500/20 text-red-400'
                                            }`}>
                                            HTTP {status}
                                        </span>
                                    )}
                                </div>
                                <div className="flex gap-1 p-1 bg-black/40 rounded-xl border border-slate-800">
                                    <button onClick={() => setViewMode('json')} className={`px-5 py-2 rounded-lg text-[9px] font-black tracking-widest transition-all ${viewMode === 'json' ? "bg-blue-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"}`}>JSON</button>
                                    <button onClick={() => setViewMode('table')} className={`px-5 py-2 rounded-lg text-[9px] font-black tracking-widest transition-all ${viewMode === 'table' ? "bg-blue-600 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"}`}>TABLE</button>
                                </div>
                            </div>

                            <div className="flex-1 overflow-auto p-8 relative z-10">
                                {loading ? (
                                    <div className="h-full flex flex-col items-center justify-center gap-4 py-32">
                                        <Loader2 size={32} className="animate-spin text-blue-500/50" />
                                        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-[0.2em] animate-pulse">Execution in progress...</span>
                                    </div>
                                ) : response ? (
                                    viewMode === 'json' ? (
                                        <pre className="text-xs font-mono text-blue-400/90 whitespace-pre-wrap break-words leading-relaxed p-6 bg-black/20 rounded-2xl border border-slate-800/50">
                                            {JSON.stringify(response, null, 2)}
                                        </pre>
                                    ) : (
                                        <JsonToTable data={response} />
                                    )
                                ) : (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-700 opacity-50 py-32">
                                        <Search size={48} strokeWidth={1} className="mb-6 opacity-20" />
                                        <p className="text-[11px] font-black uppercase tracking-[0.3em] text-center leading-relaxed">No execution data<br /><span className="text-[9px] font-medium opacity-50 tracking-normal">Send request to trigger pipeline</span></p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function JsonToTable({ data }: { data: any }) {
    if (!data) return null;
    const items = Array.isArray(data) ? data : (data && typeof data === 'object' && Array.isArray(data.items)) ? data.items : [data];
    if (items.length === 0 || typeof items[0] !== 'object' || items[0] === null) {
        return <div className="text-slate-600 text-[10px] font-mono p-4">No tabular representation available.</div>;
    }

    const headers = Object.keys(items[0]).filter(k => typeof items[0][k] !== 'object' || items[0][k] === null);

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-left text-[10px] border-collapse">
                <thead className="text-slate-600 uppercase font-black tracking-widest bg-white/[0.01]">
                    <tr>
                        {headers.map(h => <th key={h} className="py-3 px-4 border-b border-slate-800">{h}</th>)}
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                    {items.slice(0, 100).map((row: any, i: number) => (
                        <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                            {headers.map(h => (
                                <td key={h} className="py-3 px-4 text-slate-400 font-mono whitespace-nowrap">
                                    {row[h] === null ? <span className="text-slate-700 italic">null</span> : String(row[h])}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
