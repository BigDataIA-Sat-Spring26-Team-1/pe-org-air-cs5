"use client";

import React, { useEffect, useState } from "react";
import {
  Plus,
  Search,
  RefreshCw,
  TrendingUp,
  Building2,
  Activity,
  ArrowUpRight,
  Loader2,
  Clock,
  AlertCircle,
  Settings,
} from "lucide-react";
import Link from "next/link";

// Types based on backend models
interface Stats {
  companies: number;
  documents: number;
  signals: number;
  culture_data: number;
  errors: number;
  status: string;
  last_run: string | null;
}

interface Company {
  id: string;
  name: string;
  ticker: string;
  industry_id: string;
  position_factor: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [backfilling, setBackfilling] = useState(false);

  const API_BASE = (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) || "";

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsRes, companiesRes] = await Promise.all([
          fetch(`${API_BASE}/api/v1/evidence/stats`),
          fetch(`${API_BASE}/api/v1/companies/`)
        ]);

        if (statsRes.ok) setStats(await statsRes.json());
        if (companiesRes.ok) {
          const data = await companiesRes.json();
          setCompanies(data.items || []);
        }
      } catch (err) {
        console.error("Failed to fetch data:", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, [API_BASE]);

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      await fetch(`${API_BASE}/api/v1/evidence/backfill`, { method: "POST" });
    } catch (err) {
      console.error("Backfill failed:", err);
    } finally {
      setTimeout(() => setBackfilling(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#050507]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-12 w-12 animate-spin text-blue-500/50" />
          <span className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-500 animate-pulse">Initializing Hub</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050507] text-slate-100 p-8 lg:p-12 space-y-12 relative overflow-hidden">
      {/* Ambient Background Glows */}
      <div className="absolute top-[-20%] right-[-10%] w-[60%] h-[60%] bg-blue-600/10 blur-[140px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[140px] rounded-full pointer-events-none" />

      {/* Header Section */}
      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
        <div>
          <div className="flex items-center gap-3 text-blue-500 mb-3">
            <span className="h-[1px] w-12 bg-blue-500/50" />
            <span className="text-[10px] font-black uppercase tracking-[0.4em]">Strategic Intelligence</span>
          </div>
          <h2 className="text-5xl font-black text-white tracking-tight mb-2">Portfolio Overview</h2>
          <p className="text-slate-500 text-lg max-w-xl font-medium leading-relaxed">
            Orchestrating multi-vector signals for Private Equity AI readiness assessments.
          </p>
        </div>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={handleBackfill}
            disabled={backfilling || stats?.status === "running"}
            className="group relative flex items-center gap-3 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/40 text-white px-8 py-4 rounded-2xl transition-all font-black text-xs tracking-widest shadow-[0_0_40px_rgba(37,99,235,0.2)] active:scale-95"
          >
            {stats?.status === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4 group-hover:rotate-180 transition-transform duration-700" />
            )}
            {stats?.status === "running" ? "PROCESSING..." : "RUN BACKFILL"}
          </button>
          <Link
            href="/collection"
            className="group flex items-center gap-3 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-2xl transition-all font-black text-xs tracking-widest shadow-[0_0_40px_rgba(79,70,229,0.2)] active:scale-95"
          >
            <Plus className="h-4 w-4 group-hover:scale-125 transition-transform" />
            BATCH COLLECT
          </Link>
          <Link
            href="/manage"
            className="flex items-center gap-3 bg-white/[0.03] border border-white/10 hover:bg-white/[0.08] hover:border-white/20 text-white px-8 py-4 rounded-2xl transition-all font-black text-xs tracking-widest backdrop-blur-xl"
          >
            <Settings className="h-4 w-4 text-slate-400" />
            MANAGE PORTFOLIO
          </Link>
        </div>
      </div>

      {/* Premium Welcome Banner */}
      <div className="relative group z-10">
        <div className="absolute -inset-[1px] bg-gradient-to-r from-blue-600/50 via-indigo-600/50 to-purple-600/50 rounded-3xl blur-sm opacity-20 group-hover:opacity-40 transition-opacity duration-1000" />
        <div className="relative bg-[#0c0c0e]/80 border border-white/10 backdrop-blur-2xl rounded-3xl p-10 overflow-hidden shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 blur-[100px] -mr-48 -mt-48 rounded-full" />

          <div className="relative flex flex-col xl:flex-row items-center justify-between gap-12">
            <div className="max-w-3xl">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black uppercase tracking-widest mb-6">
                <Activity size={12} className="animate-pulse" /> New Feature
              </div>
              <h3 className="text-4xl font-black text-white mb-4 leading-tight">Interactive Readiness Tutorial</h3>
              <p className="text-slate-400 text-lg leading-relaxed">
                Master the Org-AI-R stack in minutes. Our guided experience covers everything from <span className="text-blue-400 font-bold">Snowflake telemetry</span> to <span className="text-indigo-400 font-bold">SEC signal auditing</span>.
              </p>
            </div>
            <Link
              href="/tutorial"
              className="group relative flex items-center gap-4 bg-white text-black px-10 py-5 rounded-[2rem] font-black tracking-widest text-xs transition-all hover:scale-105 shadow-2xl shadow-white/10 active:scale-95 whitespace-nowrap overflow-hidden"
            >
              LEARN THE PLATFORM
              <ArrowUpRight className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
            </Link>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
        <StatCard
          label="Portfolio Targets"
          value={companies.length.toString()}
          icon={<Building2 className="text-blue-500" size={20} />}
          trend="Market monitored"
          color="blue"
        />
        <StatCard
          label="Signals & Culture"
          value={((stats?.signals || 0) + (stats?.culture_data || 0)).toLocaleString()}
          icon={<TrendingUp className="text-purple-500" size={20} />}
          trend={`${stats?.culture_data || 0} Culture Vectors`}
          color="purple"
        />
        <StatCard
          label="Intelligence Docs"
          value={stats?.documents.toString() || "0"}
          icon={<Activity className="text-emerald-500" size={20} />}
          trend="EDGAR Synchronized"
          color="emerald"
        />
        <StatCard
          label="Core Status"
          value={stats?.status === "running" ? "SYNCING" : "STABLE"}
          icon={<Clock className="text-amber-500" size={20} />}
          status={stats?.status}
          color="amber"
        />
      </div>

      {/* Intelligence Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 relative z-10">
        <div className="xl:col-span-2 space-y-6">
          <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2.5rem] overflow-hidden shadow-2xl backdrop-blur-xl group">
            <div className="p-8 border-b border-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 bg-white/[0.01]">
              <h3 className="text-xl font-black text-white tracking-tight flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-blue-600/20 flex items-center justify-center border border-blue-500/30">
                  <Activity size={16} className="text-blue-400" />
                </div>
                Target Intelligence
              </h3>
              <div className="relative w-full md:w-80">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="SEARCH AUDIT TARGETS..."
                  className="w-full bg-black/40 border border-white/5 rounded-2xl py-4 pl-12 pr-6 text-[10px] font-black tracking-widest focus:outline-none focus:border-blue-500/50 transition-all shadow-inner"
                />
              </div>
            </div>

            <div className="divide-y divide-white/[0.03]">
              {companies.map((company) => (
                <div key={company.id} className="p-8 flex items-center justify-between hover:bg-white/[0.02] transition-all cursor-pointer group/row">
                  <div className="flex items-center gap-6">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-600/10 to-indigo-600/10 rounded-2xl flex items-center justify-center border border-white/5 group-hover/row:border-blue-500/30 transition-all shadow-inner font-black text-xl text-blue-400 tracking-tighter">
                      {company.ticker}
                    </div>
                    <div>
                      <h4 className="font-black text-xl text-white tracking-tight group-hover/row:text-blue-400 transition-colors">{company.name}</h4>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest">{company.id.substring(0, 8)}</span>
                        <span className="h-1 w-1 rounded-full bg-slate-800" />
                        <span className="text-[10px] font-black text-slate-600 uppercase tracking-widest font-mono">SEC-VERIFIED</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-12 items-center">
                    <Link
                      href={`/audit/${company.id}`}
                      className="flex items-center gap-3 bg-white/[0.03] border border-white/5 hover:bg-blue-600 hover:border-blue-500 text-slate-400 hover:text-white px-6 py-3 rounded-xl text-[10px] font-black tracking-widest transition-all shadow-xl"
                    >
                      VIEW AUDIT <ArrowUpRight size={14} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Activity */}
        <div className="space-y-6">
          <div className="bg-[#0c0c0e]/50 border border-white/5 rounded-[2.5rem] p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden h-fit">
            <h3 className="text-sm font-black text-white uppercase tracking-[0.3em] mb-8 flex items-center gap-3">
              <Activity size={14} className="text-purple-500" />
              Live Activity
            </h3>
            <div className="space-y-8">
              <ActivityItem title="Signal Ingestion" detail="CAT AI-Hiring Data Collected" time="2M AGO" type="success" />
              <ActivityItem title="Filing Analysis" detail="DE 10-K Processed" time="15M AGO" type="info" />
              <ActivityItem title="System Sync" detail="Vector Index Rebuilt" time="1H AGO" type="success" />
              <ActivityItem title="Model Alert" detail="Scored Below Confidence" time="2H AGO" type="error" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, trend, status, color }: { label: string; value: string; icon: React.ReactNode; trend?: string; status?: string; color: string }) {
  const colorMap: Record<string, string> = {
    blue: "text-blue-500 bg-blue-500/10 border-blue-500/20",
    purple: "text-purple-500 bg-purple-500/10 border-purple-500/20",
    emerald: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20",
    amber: "text-amber-500 bg-amber-500/10 border-amber-500/20",
  };

  return (
    <div className="bg-[#0c0c0e]/80 border border-white/5 rounded-[2rem] p-8 shadow-xl overflow-hidden backdrop-blur-3xl min-h-[160px] flex flex-col justify-between group hover:border-white/10 transition-colors">
      <div className="flex justify-between items-start">
        <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.2em]">{label}</p>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center border transition-transform duration-500 group-hover:scale-110 ${colorMap[color]}`}>
          {icon}
        </div>
      </div>
      <div>
        <h3 className="text-4xl font-black text-white tracking-tighter mt-4">{value}</h3>
        {status === "running" ? (
          <div className="mt-3 flex items-center gap-2 text-amber-500 text-[9px] font-black uppercase tracking-widest animate-pulse">
            <Loader2 size={10} className="animate-spin" />
            Running...
          </div>
        ) : trend ? (
          <p className="text-slate-600 text-[9px] font-black uppercase tracking-widest mt-3 flex items-center gap-2">
            <span className="w-1 h-1 rounded-full bg-slate-800" />
            {trend}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function ActivityItem({ title, detail, time, type }: { title: string; detail: string; time: string; type: 'success' | 'error' | 'info' }) {
  const dotMap = {
    success: 'bg-emerald-500 shadow-emerald-500/50',
    error: 'bg-red-500 shadow-red-500/50',
    info: 'bg-blue-500 shadow-blue-500/50'
  };

  return (
    <div className="flex gap-6 group/item">
      <div className="flex flex-col items-center">
        <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${dotMap[type]} shadow-[0_0_10px_2px_rgba(0,0,0,1)] relative z-10 transition-transform group-hover/item:scale-125`} />
        <div className="w-[1px] flex-1 bg-white/[0.03] my-2" />
      </div>
      <div className="flex-1 pb-2">
        <div className="flex justify-between items-start mb-1">
          <h5 className="font-black text-[11px] text-white uppercase tracking-widest">{title}</h5>
          <span className="text-[9px] text-slate-600 font-black tracking-tighter">{time}</span>
        </div>
        <p className="text-xs text-slate-500 font-medium group-hover/item:text-slate-300 transition-colors uppercase tracking-tight">{detail}</p>
      </div>
    </div>
  );
}
