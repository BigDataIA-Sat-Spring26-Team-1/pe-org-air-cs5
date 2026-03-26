"use client";
import { useState, useEffect } from "react";
import { Plug, Copy, Check, ChevronDown, ChevronUp, Zap, BookOpen, Database, Activity } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
const MCP_URL = typeof window !== "undefined"
  ? `${window.location.protocol}//${window.location.hostname}:3001`
  : "http://localhost:3001";

interface ToolParam {
  name: string;
  type: string;
  required: boolean;
  description: string;
  values?: string[];
}

interface Tool {
  name: string;
  description: string;
  parameters: ToolParam[];
}

interface Prompt {
  name: string;
  description: string;
  arguments: { name: string; required: boolean }[];
  workflow: string;
}

interface Resource {
  uri: string;
  name: string;
  description: string;
  example: Record<string, unknown>;
}

interface MCPData {
  tools: Tool[];
  prompts: Prompt[];
  resources: Resource[];
}

type Tab = "connection" | "tools" | "prompts" | "resources";

export default function MCPPage() {
  const [activeTab, setActiveTab] = useState<Tab>("connection");
  const [data, setData] = useState<MCPData | null>(null);
  const [mcpHealth, setMcpHealth] = useState<"checking" | "ok" | "error">("checking");
  const [copied, setCopied] = useState(false);
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/agent-ui/mcp-tools`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {});

    fetch(`${API_BASE.replace("8000", "3001")}/health`)
      .then((r) => r.ok ? setMcpHealth("ok") : setMcpHealth("error"))
      .catch(() => setMcpHealth("error"));
  }, []);

  const claudeConfig = JSON.stringify(
    {
      mcpServers: {
        "pe-orgair": {
          url: "http://localhost:3001/sse",
        },
      },
    },
    null,
    2
  );

  const copyConfig = () => {
    navigator.clipboard.writeText(claudeConfig).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "connection", label: "Connection", icon: <Plug size={16} /> },
    { id: "tools", label: `Tools (${data?.tools.length ?? 6})`, icon: <Zap size={16} /> },
    { id: "prompts", label: `Prompts (${data?.prompts.length ?? 2})`, icon: <BookOpen size={16} /> },
    { id: "resources", label: `Resources (${data?.resources.length ?? 2})`, icon: <Database size={16} /> },
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-violet-600/20 rounded-xl flex items-center justify-center border border-violet-600/30">
          <Plug className="w-6 h-6 text-violet-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">MCP Server</h1>
          <p className="text-slate-400 text-sm">Model Context Protocol — connect Claude Desktop or any MCP client</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${mcpHealth === "ok" ? "bg-emerald-400" : mcpHealth === "error" ? "bg-red-400" : "bg-yellow-400 animate-pulse"}`} />
          <span className={`text-sm font-medium ${mcpHealth === "ok" ? "text-emerald-400" : mcpHealth === "error" ? "text-red-400" : "text-yellow-400"}`}>
            {mcpHealth === "ok" ? "Connected" : mcpHealth === "error" ? "Unreachable" : "Checking…"}
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-slate-900 rounded-xl p-1 border border-slate-800">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center ${
              activeTab === t.id
                ? "bg-violet-600 text-white"
                : "text-slate-400 hover:text-slate-100"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* CONNECTION TAB */}
      {activeTab === "connection" && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-1">Server Details</h2>
            <p className="text-slate-400 text-sm mb-4">MCP server runs on port 3001 with SSE transport.</p>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: "SSE Endpoint", value: "http://localhost:3001/sse" },
                { label: "HTTP Bridge", value: "http://localhost:3001/tools/{name}" },
                { label: "Transport", value: "SSE (Server-Sent Events)" },
                { label: "Protocol", value: "MCP v1.0" },
              ].map(({ label, value }) => (
                <div key={label} className="bg-slate-800/50 rounded-lg p-3">
                  <div className="text-xs text-slate-500 mb-1">{label}</div>
                  <div className="text-sm text-slate-200 font-mono">{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">Claude Desktop Config</h2>
                <p className="text-slate-400 text-sm">Add this to your <code className="text-violet-400">claude_desktop_config.json</code></p>
              </div>
              <button
                onClick={copyConfig}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-700 rounded-lg text-sm font-medium transition-colors"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <pre className="bg-[#0c0c0e] rounded-lg p-4 text-sm text-emerald-300 font-mono overflow-x-auto border border-slate-800">
              {claudeConfig}
            </pre>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">Setup Instructions</h2>
            <ol className="space-y-3">
              {[
                "Ensure Docker Compose is running: docker compose -f docker/docker-compose.yml up -d",
                "Verify MCP server health: curl http://localhost:3001/health",
                "Open Claude Desktop → Settings → Developer → Edit Config",
                "Paste the config JSON shown above into claude_desktop_config.json",
                "Restart Claude Desktop — the pe-orgair MCP server will appear in your tools list",
                "Use the Prompts tab to copy ready-made workflow prompts into Claude Desktop",
              ].map((step, i) => (
                <li key={i} className="flex gap-3">
                  <div className="w-6 h-6 bg-violet-600/20 rounded-full flex items-center justify-center text-violet-400 text-xs font-bold shrink-0 mt-0.5">
                    {i + 1}
                  </div>
                  <span className="text-slate-300 text-sm">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* TOOLS TAB */}
      {activeTab === "tools" && (
        <div className="space-y-3">
          {(data?.tools ?? []).map((tool) => (
            <div key={tool.name} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedTool(expandedTool === tool.name ? null : tool.name)}
                className="w-full flex items-center justify-between p-5 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-violet-600/20 rounded-lg flex items-center justify-center">
                    <Zap size={14} className="text-violet-400" />
                  </div>
                  <div className="text-left">
                    <div className="font-mono text-sm font-semibold text-violet-300">{tool.name}</div>
                    <div className="text-slate-400 text-xs mt-0.5">{tool.description}</div>
                  </div>
                </div>
                {expandedTool === tool.name ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
              </button>
              {expandedTool === tool.name && (
                <div className="border-t border-slate-800 p-5">
                  <div className="text-xs text-slate-500 uppercase tracking-wider mb-3">Parameters</div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-slate-500 border-b border-slate-800">
                          <th className="pb-2 pr-4">Name</th>
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4">Required</th>
                          <th className="pb-2">Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tool.parameters.map((p) => (
                          <tr key={p.name} className="border-b border-slate-800/50 last:border-0">
                            <td className="py-2 pr-4 font-mono text-emerald-300">{p.name}</td>
                            <td className="py-2 pr-4 text-blue-300">{p.type}</td>
                            <td className="py-2 pr-4">
                              <span className={`px-2 py-0.5 rounded text-xs ${p.required ? "bg-red-900/30 text-red-300" : "bg-slate-800 text-slate-400"}`}>
                                {p.required ? "required" : "optional"}
                              </span>
                            </td>
                            <td className="py-2 text-slate-400">
                              {p.description}
                              {p.values && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {p.values.map((v) => (
                                    <span key={v} className="px-1.5 py-0.5 bg-slate-800 rounded text-xs text-slate-300 font-mono">{v}</span>
                                  ))}
                                </div>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* PROMPTS TAB */}
      {activeTab === "prompts" && (
        <div className="space-y-4">
          {(data?.prompts ?? []).map((prompt) => (
            <div key={prompt.name} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <button
                onClick={() => setExpandedPrompt(expandedPrompt === prompt.name ? null : prompt.name)}
                className="w-full flex items-center justify-between p-5 hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-600/20 rounded-lg flex items-center justify-center">
                    <BookOpen size={14} className="text-blue-400" />
                  </div>
                  <div className="text-left">
                    <div className="font-mono text-sm font-semibold text-blue-300">{prompt.name}</div>
                    <div className="text-slate-400 text-xs mt-0.5">{prompt.description}</div>
                  </div>
                </div>
                {expandedPrompt === prompt.name ? <ChevronUp size={16} className="text-slate-500" /> : <ChevronDown size={16} className="text-slate-500" />}
              </button>
              {expandedPrompt === prompt.name && (
                <div className="border-t border-slate-800 p-5 space-y-4">
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Arguments</div>
                    <div className="flex gap-2">
                      {prompt.arguments.map((a) => (
                        <span key={a.name} className="px-2 py-1 bg-blue-900/20 border border-blue-800/30 rounded text-blue-300 text-xs font-mono">
                          {a.name} {a.required && <span className="text-red-400">*</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Workflow</div>
                    <pre className="bg-[#0c0c0e] rounded-lg p-4 text-sm text-slate-300 font-mono whitespace-pre-wrap border border-slate-800 leading-relaxed">
                      {prompt.workflow}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* RESOURCES TAB */}
      {activeTab === "resources" && (
        <div className="space-y-4">
          {(data?.resources ?? []).map((res) => (
            <div key={res.uri} className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-8 h-8 bg-emerald-600/20 rounded-lg flex items-center justify-center shrink-0">
                  <Database size={14} className="text-emerald-400" />
                </div>
                <div>
                  <div className="font-semibold text-slate-100">{res.name}</div>
                  <div className="font-mono text-xs text-emerald-300 mt-0.5">{res.uri}</div>
                  <div className="text-slate-400 text-sm mt-1">{res.description}</div>
                </div>
              </div>
              <div className="text-xs text-slate-500 uppercase tracking-wider mb-2">Example Value</div>
              <pre className="bg-[#0c0c0e] rounded-lg p-4 text-sm text-emerald-300 font-mono overflow-x-auto border border-slate-800">
                {JSON.stringify(res.example, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
