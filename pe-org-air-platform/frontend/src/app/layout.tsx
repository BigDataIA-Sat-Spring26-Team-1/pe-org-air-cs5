import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { LayoutDashboard, FileSearch, Settings, BookOpen, BarChart3, Database, Terminal, TrendingUp, Brain, FileText, Plug, GitBranch, DollarSign, Activity } from "lucide-react";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PE OrgAIR | AI Intelligence",
  description: "AI Maturity Intelligence for Private Equity",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex text-slate-100`}>
        {/* Sidebar */}
        <aside className="w-64 border-r border-slate-800 bg-[#0c0c0e] flex flex-col fixed h-full z-50">
          <div className="p-6">
            <div className="flex items-center gap-3 mb-8">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <Database className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold tracking-tight">OrgAIR</h1>
            </div>

            <nav className="space-y-1">
              <NavItem href="/" icon={<LayoutDashboard size={20} />} label="Dashboard" />
              <NavItem href="/analytics" icon={<BarChart3 size={20} />} label="Analytics" />
              <NavItem href="/readiness" icon={<TrendingUp size={20} />} label="AI Readiness" />
              <NavItem href="/explorer" icon={<FileSearch size={20} />} label="SEC Explorer" />
              <NavItem href="/rag" icon={<Brain size={20} />} label="RAG Analysis" />
              <NavItem href="/documents" icon={<FileText size={20} />} label="Documents" />
              <NavItem href="/mcp-server" icon={<Plug size={20} />} label="MCP Server" />
              <NavItem href="/workflow" icon={<GitBranch size={20} />} label="Agentic Workflow" />
              <NavItem href="/investments" icon={<DollarSign size={20} />} label="Investment ROI" />
              <NavItem href="/observability" icon={<Activity size={20} />} label="Observability" />
              <NavItem href="/manage" icon={<Settings size={20} />} label="Management" />
              <NavItem href="/playground" icon={<Terminal size={20} />} label="API Playground" />
              <NavItem href="/tutorial" icon={<BookOpen size={20} />} label="Tutorials" />
            </nav>
          </div>

          <div className="mt-auto p-6 border-t border-slate-800">
            <nav className="space-y-1">
              <Link
                href="/platform-docs"
                className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 text-slate-400 hover:text-slate-100 hover:bg-white/5"
              >
                <BookOpen size={20} />
                <span>Documentation</span>
              </Link>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || ''}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 text-slate-400 hover:text-slate-100 hover:bg-white/5"
              >
                <Terminal size={20} />
                <span>Swagger Docs</span>
              </a>
            </nav>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 ml-64 bg-[#09090b]">
          {children}
        </main>
      </body>
    </html>
  );
}

function NavItem({ href, icon, label, active = false }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${active
        ? "bg-blue-600/10 text-blue-400 font-medium"
        : "text-slate-400 hover:text-slate-100 hover:bg-white/5"
        }`}
    >
      {icon}
      <span>{label}</span>
    </Link>
  );
}
