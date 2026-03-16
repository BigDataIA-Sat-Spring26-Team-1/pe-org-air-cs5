"use client";

import React, { useState } from "react";
import {
    ChevronRight,
    ChevronLeft,
    CheckCircle2,
    Circle,
    Play,
    Terminal,
    Settings,
    Database,
    LayoutDashboard,
    Box,
    Cpu,
    Copy,
    Check,
    Cloud,
    Server,
    FileText,
    Globe,
    Lock,
    Shield,
    ArrowRight,
    Code,
    Layers,
    FileCheck,
    Search
} from "lucide-react";

const STEPS = [
    {
        id: "intro",
        title: "Introduction",
        duration: "2 min",
        icon: <Play className="w-5 h-5" />,
        content: (
            <div className="space-y-6">
                <div className="p-8 rounded-3xl bg-blue-600/10 border border-blue-500/20">
                    <h3 className="text-2xl font-bold text-blue-400 mb-4">Welcome to PE Org-AI-R</h3>
                    <p className="text-slate-300 leading-relaxed text-lg">
                        You are about to deploy a next-generation AI intelligence platform designed for Private Equity due diligence.
                        This system autonomously aggregates signals from SEC filings, patent databases, and job boards to compute
                        an "AI Maturity Index" for target companies.
                    </p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                        <h4 className="font-semibold text-white mb-2">What you'll learn</h4>
                        <ul className="space-y-2 text-slate-400">
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Deploying the Async Master Pipeline</li>
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Configuring Snowflake Vector Tables</li>
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Navigating the Intelligence Hub</li>
                        </ul>
                    </div>
                    <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
                        <h4 className="font-semibold text-white mb-2">Platform Goals</h4>
                        <ul className="space-y-2 text-slate-400">
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Reduce due diligence time by 90%</li>
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Identify hidden AI implementation risks</li>
                            <li className="flex gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-1" /> Deliver sub-second metrics via Redis</li>
                        </ul>
                    </div>
                </div>
            </div>
        )
    },
    {
        id: "prereq",
        title: "Prerequisites",
        duration: "3 min",
        icon: <Settings className="w-5 h-5" />,
        content: (
            <div className="space-y-6">
                <p className="text-lg text-slate-300">Before we begin, ensure your local machine is equipped with the following enterprise tools:</p>
                <div className="space-y-4">
                    {[
                        { title: "Docker & Docker Compose", desc: "For container orchestration and service isolation.", version: "V2.x+" },
                        { title: "Snowflake Account", desc: "Required for long-term intelligence storage and heavy analytical queries.", version: "Standard/Enterprise" },
                        { title: "Python Runtime", desc: "Used for local development and running the master pipeline CLI.", version: "3.12+" },
                        { title: "AWS Account", desc: "S3 Bucket access for storing raw PDF filings and unstructured data.", version: "Any" },
                        { title: "PatentsView API Key", desc: "Access to USPTO patent data for innovation scoring.", version: "Free Tier" }
                    ].map((item, i) => (
                        <div key={i} className="flex items-center gap-6 p-6 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
                            <div className="w-12 h-12 rounded-full bg-blue-600/20 flex items-center justify-center shrink-0 border border-blue-500/30">
                                <Check className="w-5 h-5 text-blue-400" />
                            </div>
                            <div className="flex-1">
                                <h4 className="font-bold text-white text-lg">{item.title}</h4>
                                <p className="text-slate-400">{item.desc}</p>
                            </div>
                            <div className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs font-mono text-slate-300">
                                {item.version}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )
    },
    {
        id: "config",
        title: "Environment Configuration",
        duration: "5 min",
        icon: <Database className="w-5 h-5" />,
        content: (
            <div className="space-y-6">
                <p className="text-lg text-slate-300">The platform uses a centralized <span className="font-mono text-blue-400">.env</span> file for secure credential management.</p>

                <div className="rounded-2xl bg-[#0c0c0e] border border-white/10 overflow-hidden">
                    <div className="flex items-center justify-between px-6 py-3 bg-white/5 border-b border-white/10">
                        <span className="text-xs font-mono text-slate-500">.env</span>
                        <button className="text-xs flex items-center gap-2 text-blue-400 hover:text-blue-300 transition-colors">
                            <Copy className="w-3 h-3" /> Copy
                        </button>
                    </div>
                    <pre className="p-6 text-sm font-mono text-blue-100 overflow-x-auto">
                        {`# === Snowflake Settings ===
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=PE_ORGAIR
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_ROLE=your_role

# === Infrastructure ===
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
NEXT_PUBLIC_API_URL="http://localhost:8000"

# === Data Providers ===
PATENTSVIEW_API_KEY=your_key
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=your_bucket
AWS_REGION=us-east-1

# === App Info ===
APP_NAME=PE Org-AI-R Platform
APP_VERSION=1.0.0`}
                    </pre>
                </div>
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex gap-4 items-start">
                    <div className="p-2 rounded-lg bg-amber-500/20 shrink-0">
                        <Settings className="w-5 h-5 text-amber-500" />
                    </div>
                    <div>
                        <h5 className="font-bold text-amber-500 mb-1">Pro Tip: Snowflake Roles</h5>
                        <p className="text-slate-400 text-sm">Ensure your user has permissions to create tables or use a dedicated schema for the assessment data.</p>
                    </div>
                </div>
            </div>
        )
    },
    {
        id: "deployment",
        title: "Deployment",
        duration: "10 min",
        icon: <Box className="w-5 h-5" />,
        content: (
            <div className="space-y-6">
                <p className="text-lg text-slate-300">Launch the entire ecosystem with a single command. Docker handles the frontend build, backend initialization, and Redis caching layers.</p>
                <div className="rounded-2xl bg-black border border-white/10 overflow-hidden shadow-2xl">
                    <div className="flex items-center gap-2 px-6 py-3 bg-white/5 border-b border-white/10">
                        <div className="w-3 h-3 rounded-full bg-red-500/50" />
                        <div className="w-3 h-3 rounded-full bg-amber-500/50" />
                        <div className="w-3 h-3 rounded-full bg-green-500/50" />
                        <span className="ml-4 text-xs font-mono text-slate-500">Terminal — bash</span>
                    </div>
                    <div className="p-6 font-mono text-sm">
                        <div className="flex gap-3 text-emerald-400">
                            <span>$</span>
                            <span>docker compose --env-file .env -f docker/docker-compose.yml up --build</span>
                        </div>
                        <div className="mt-4 space-y-1 text-slate-500">
                            <p>[+] Building frontend 42.5s</p>
                            <p>[+] Building api 12.1s</p>
                            <p>[+] Running 3/3</p>
                            <p className="text-blue-400">⠏ Container redis Running</p>
                            <p className="text-blue-400">⠏ Container api Running</p>
                            <p className="text-blue-400">⠏ Container frontend Running</p>
                        </div>
                    </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <h5 className="text-white font-semibold flex items-center gap-2 mb-2">
                            <LayoutDashboard className="w-4 h-4 text-blue-400" />
                            Frontend Hub
                        </h5>
                        <p className="text-slate-400 text-sm italic">http://localhost:3000</p>
                    </div>
                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <h5 className="text-white font-semibold flex items-center gap-2 mb-2">
                            <Cpu className="w-4 h-4 text-emerald-400" />
                            API Backbone
                        </h5>
                        <p className="text-slate-400 text-sm italic">http://localhost:8000</p>
                    </div>
                </div>
            </div>
        )
    },
    {
        id: "dashboard",
        title: "Exploring the Hub",
        duration: "5 min",
        icon: <LayoutDashboard className="w-5 h-5" />,
        content: (
            <div className="space-y-6">
                <p className="text-lg text-slate-300">Navigate to the main dashboard to see the live intelligence engine in action.</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                        { title: "Portfolio Management", desc: "Add industries and target companies for assessment.", icon: <Box className="w-5 h-5" /> },
                        { title: "Real-time Scoring", desc: "View AI maturity scores computed from multi-vector signals.", icon: <CheckCircle2 className="w-5 h-5" /> },
                        { title: "Deep-dive Audit", desc: "Interact with semantic segments extracted from SEC filings.", icon: <Terminal className="w-5 h-5" /> }
                    ].map((item, i) => (
                        <div key={i} className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-blue-500/30 transition-all">
                            <div className="text-blue-400 mb-4">{item.icon}</div>
                            <h4 className="text-white font-bold mb-2">{item.title}</h4>
                            <p className="text-slate-400 text-xs leading-relaxed">{item.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        )
    },
    {
        id: "architecture",
        title: "Architecture",
        duration: "10 min",
        icon: <Cpu className="w-5 h-5" />,
        content: (
            <div className="space-y-12">
                {/* Section 1: Code Flow & Pipeline Architecture */}
                <div className="space-y-6">
                    <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Layers className="w-6 h-6 text-blue-400" />
                        Code Flow & Pipeline
                    </h3>
                    <div className="relative p-8 rounded-3xl bg-[#0c0c0e] border border-white/10">
                        {/* Flow Diagram */}
                        <div className="flex flex-col gap-8 relative z-10">

                            {/* Trigger & Orchestration */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm text-slate-400 font-mono uppercase tracking-widest mb-2">
                                        <Play className="w-4 h-4 text-emerald-500" /> Trigger
                                    </div>
                                    <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                        <div className="flex items-center gap-3 mb-2">
                                            <Globe className="w-4 h-4 text-blue-400" />
                                            <span className="font-mono text-sm text-white">POST /collect</span>
                                        </div>
                                        <p className="text-xs text-slate-400">Initiates MasterPipeline for target</p>
                                    </div>
                                </div>

                                <div className="space-y-2 relative">
                                    <div className="flex items-center gap-2 text-sm text-slate-400 font-mono uppercase tracking-widest mb-2">
                                        <Cpu className="w-4 h-4 text-blue-500" /> Orchestration
                                    </div>
                                    <div className="p-4 rounded-xl bg-blue-600/10 border border-blue-500/30">
                                        <div className="font-bold text-white text-sm mb-1">MasterPipeline</div>
                                        <p className="text-xs text-blue-200">Spawns concurrent asyncio tasks</p>
                                    </div>
                                </div>
                            </div>

                            {/* Collection Layer */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-sm text-slate-400 font-mono uppercase tracking-widest mb-2">
                                    <ArrowRight className="w-4 h-4 text-slate-600" /> Collection Parsers
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 dashed-border">
                                        <div className="flex items-center gap-2 mb-2">
                                            <FileText className="w-4 h-4 text-amber-500" />
                                            <span className="font-semibold text-white text-sm">SEC Pipeline</span>
                                        </div>
                                        <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                                            <li>Fetch HTML/PDF filings</li>
                                            <li>NLP Semantic Chunking</li>
                                            <li>Regex Extraction (Item 1, 1A)</li>
                                        </ul>
                                    </div>
                                    <div className="p-4 rounded-xl bg-white/5 border border-white/10 dashed-border">
                                        <div className="flex items-center gap-2 mb-2">
                                            <Search className="w-4 h-4 text-purple-500" />
                                            <span className="font-semibold text-white text-sm">Signal Pipeline</span>
                                        </div>
                                        <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                                            <li>JobSpy (Job Boards)</li>
                                            <li>PatentsView API</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Ingestion & Persistence */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm text-slate-400 font-mono uppercase tracking-widest mb-2">
                                        <Database className="w-4 h-4 text-cyan-500" /> Ingestion & Persistence
                                    </div>
                                    <div className="p-4 rounded-xl bg-cyan-900/10 border border-cyan-500/30">
                                        <div className="font-bold text-white text-sm mb-1">SnowflakeDAO</div>
                                        <p className="text-xs text-cyan-200 mb-2">MERGE INTO (Idempotency)</p>
                                        <div className="flex gap-2">
                                            <span className="px-2 py-1 bg-black/40 rounded text-[10px] font-mono text-slate-300">TABLE: Companies</span>
                                            <span className="px-2 py-1 bg-black/40 rounded text-[10px] font-mono text-slate-300">TABLE: Signals</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-sm text-slate-400 font-mono uppercase tracking-widest mb-2">
                                        <CheckCircle2 className="w-4 h-4 text-green-500" /> Post-Processing
                                    </div>
                                    <div className="p-4 rounded-xl bg-green-900/10 border border-green-500/30">
                                        <div className="font-bold text-white text-sm mb-1">Intelligence Scoring</div>
                                        <p className="text-xs text-green-200">0-100 Weighted Calculation</p>
                                        <div className="mt-2 text-[10px] font-mono text-slate-400">{'->'} Saved to company_signal_summary</div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>

                {/* Section 2: Infrastructure */}
                <div className="space-y-6">
                    <h3 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Server className="w-6 h-6 text-emerald-400" />
                        Infrastructure
                    </h3>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                        {/* Docker Container */}
                        <div className="lg:col-span-4 rounded-3xl bg-[#1e1e24] border-2 border-dashed border-slate-700 p-6 relative">
                            <div className="absolute -top-3 left-6 px-2 bg-[#09090b] text-slate-400 text-xs font-mono flex items-center gap-2">
                                <Box className="w-3 h-3" /> DOCKER COMPOSE
                            </div>

                            <div className="space-y-4">
                                {/* Frontend */}
                                <div className="p-4 rounded-xl bg-[#0c0c0e] border border-white/10 flex items-center gap-4">
                                    <div className="p-2 bg-white/5 rounded-lg"><LayoutDashboard className="w-5 h-5 text-white" /></div>
                                    <div>
                                        <div className="text-white font-bold text-sm">Next.js Frontend</div>
                                        <div className="text-xs text-slate-500">SSR + Client Fetch</div>
                                    </div>
                                </div>

                                {/* Backend */}
                                <div className="p-4 rounded-xl bg-[#0c0c0e] border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.1)] flex items-center gap-4">
                                    <div className="p-2 bg-blue-600/20 rounded-lg"><Cpu className="w-5 h-5 text-blue-400" /></div>
                                    <div>
                                        <div className="text-white font-bold text-sm">FastAPI "Brain"</div>
                                        <div className="text-xs text-slate-500">Singleton Pool</div>
                                    </div>
                                </div>

                                {/* Redis */}
                                <div className="p-4 rounded-xl bg-[#0c0c0e] border border-red-500/20 flex items-center gap-4">
                                    <div className="p-2 bg-red-600/10 rounded-lg"><Database className="w-5 h-5 text-red-500" /></div>
                                    <div>
                                        <div className="text-white font-bold text-sm">Redis</div>
                                        <div className="text-xs text-slate-500">Hot Cache (Stats)</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="lg:col-span-1 hidden lg:flex items-center justify-center">
                            <ArrowRight className="w-8 h-8 text-slate-700" />
                        </div>

                        {/* External Services */}
                        <div className="lg:col-span-7 space-y-4">
                            {/* Snowflake */}
                            <div className="p-6 rounded-3xl bg-[#0c0c0e] border border-cyan-500/30 flex flex-col md:flex-row gap-6 items-center">
                                <div className="w-16 h-16 rounded-2xl bg-cyan-900/10 flex items-center justify-center shrink-0">
                                    <Database className="w-8 h-8 text-cyan-400" />
                                </div>
                                <div className="flex-1">
                                    <h4 className="text-lg font-bold text-white mb-2">Snowflake Data Cloud</h4>
                                    <div className="grid grid-cols-2 gap-2">
                                        <div className="px-3 py-2 rounded-lg bg-white/5 text-xs text-slate-300 font-mono border border-white/5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" /> VARIANT (JSON)
                                        </div>
                                        <div className="px-3 py-2 rounded-lg bg-white/5 text-xs text-slate-300 font-mono border border-white/5 flex items-center gap-2">
                                            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" /> Structured Tables
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* AWS S3 */}
                            <div className="p-6 rounded-3xl bg-[#0c0c0e] border border-amber-500/30 flex flex-col md:flex-row gap-6 items-center">
                                <div className="w-16 h-16 rounded-2xl bg-amber-900/10 flex items-center justify-center shrink-0">
                                    <Cloud className="w-8 h-8 text-amber-400" />
                                </div>
                                <div className="flex-1">
                                    <h4 className="text-lg font-bold text-white mb-2">AWS S3</h4>
                                    <code className="block text-xs font-mono text-amber-500 mb-2">e-orgair-bucket-us-east-1</code>
                                    <div className="flex gap-2">
                                        <div className="px-2 py-1 rounded bg-white/5 border border-white/5 text-[10px] text-slate-400 flex items-center gap-1">
                                            <FileText className="w-3 h-3" /> PDF
                                        </div>
                                        <div className="px-2 py-1 rounded bg-white/5 border border-white/5 text-[10px] text-slate-400 flex items-center gap-1">
                                            <FileText className="w-3 h-3" /> HTML
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        )
    }
];

export default function TutorialPage() {
    const [currentStep, setCurrentStep] = useState(0);
    const [completedSteps, setCompletedSteps] = useState<number[]>([]);

    const handleNext = () => {
        if (currentStep < STEPS.length - 1) {
            if (!completedSteps.includes(currentStep)) {
                setCompletedSteps([...completedSteps, currentStep]);
            }
            setCurrentStep(currentStep + 1);
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    };

    const step = STEPS[currentStep];
    const progress = ((currentStep + 1) / STEPS.length) * 100;

    return (
        <div className="min-h-screen bg-[#09090b] text-slate-100 flex flex-col md:flex-row">
            {/* Tutorial Sidebar */}
            <aside className="w-full md:w-80 border-r border-slate-800 bg-[#0c0c0e] p-8 flex flex-col sticky top-0 h-fit md:h-screen">
                <div className="mb-8">
                    <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Learning Path</h2>
                    <h1 className="text-xl font-bold">Platform Quickstart</h1>
                </div>

                <div className="space-y-2 flex-1">
                    {STEPS.map((s, i) => {
                        const isCompleted = completedSteps.includes(i) || i < currentStep;
                        const isActive = i === currentStep;

                        return (
                            <button
                                key={s.id}
                                onClick={() => setCurrentStep(i)}
                                className={`w-full group flex items-start gap-4 p-4 rounded-2xl transition-all duration-200 text-left ${isActive ? "bg-blue-600/10 border border-blue-500/20" : "hover:bg-white/5 border border-transparent"
                                    }`}
                            >
                                <div className={`mt-1 shrink-0 ${isActive ? "text-blue-400" : isCompleted ? "text-emerald-500" : "text-slate-600"}`}>
                                    {isCompleted ? <CheckCircle2 className="w-5 h-5" /> : isActive ? <Circle className="w-5 h-5 fill-blue-400/20" /> : <Circle className="w-5 h-5" />}
                                </div>
                                <div>
                                    <h3 className={`text-sm font-semibold ${isActive ? "text-blue-400" : "text-slate-300 group-hover:text-slate-100"}`}>
                                        {i + 1}. {s.title}
                                    </h3>
                                    <p className="text-xs text-slate-500 mt-0.5">{s.duration}</p>
                                </div>
                            </button>
                        );
                    })}
                </div>

                <div className="mt-8 pt-8 border-t border-slate-800">
                    <div className="flex justify-between text-xs text-slate-500 mb-2">
                        <span>Overall Progress</span>
                        <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-500 transition-all duration-500 ease-out"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            </aside>

            {/* Content Area */}
            <main className="flex-1 max-w-4xl mx-auto px-6 py-12 md:px-16 md:py-20 flex flex-col">
                {/* Header */}
                <div className="mb-12 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-blue-600/20 flex items-center justify-center border border-blue-500/30 text-blue-400">
                            {step.icon}
                        </div>
                        <div>
                            <p className="text-xs font-mono text-blue-400 uppercase tracking-widest">Step {currentStep + 1} of {STEPS.length}</p>
                            <h2 className="text-3xl font-bold tracking-tight mt-1">{step.title}</h2>
                        </div>
                    </div>
                    <div className="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-400 text-sm">
                        <span>Estimated Duration:</span>
                        <span className="text-white font-medium">{step.duration}</span>
                    </div>
                </div>

                {/* Dynamic Step Content */}
                <div className="flex-1 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {step.content}
                </div>

                {/* Footer Navigation */}
                <div className="mt-16 pt-8 border-t border-slate-800 flex items-center justify-between">
                    <button
                        onClick={handlePrev}
                        disabled={currentStep === 0}
                        className={`flex items-center gap-2 px-6 py-3 rounded-2xl transition-all ${currentStep === 0 ? "opacity-0 pointer-events-none" : "hover:bg-white/5 text-slate-400 hover:text-white"
                            }`}
                    >
                        <ChevronLeft className="w-5 h-5" />
                        <span className="font-semibold">Back</span>
                    </button>

                    {currentStep === STEPS.length - 1 ? (
                        <button
                            onClick={() => window.location.href = "/"}
                            className="group flex items-center gap-3 px-8 py-4 rounded-2xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-all shadow-lg shadow-emerald-900/20"
                        >
                            Finish Tutorial
                            <Check className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        </button>
                    ) : (
                        <button
                            onClick={handleNext}
                            className="group flex items-center gap-3 px-8 py-4 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold transition-all shadow-lg shadow-blue-900/20"
                        >
                            Next Step
                            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                    )}
                </div>
            </main>
        </div>
    );
}

