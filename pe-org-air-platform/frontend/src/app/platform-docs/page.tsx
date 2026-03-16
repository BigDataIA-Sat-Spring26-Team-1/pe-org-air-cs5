import fs from 'fs';
import path from 'path';
import { BookOpen } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const dynamic = "force-dynamic";

export default async function DocumentationPage() {
    let markdown = "# Documentation Not Found\n\nCould not locate the README.md file.";

    // Try to find README in common locations
    const possiblePaths = [
        path.join(process.cwd(), 'PROJECT_README.md'),  // Mounted via Docker volume
        path.join(process.cwd(), 'README.md'),          // Standard fallback
    ];

    for (const p of possiblePaths) {
        try {
            if (fs.existsSync(p)) {
                markdown = fs.readFileSync(p, 'utf8');
                break;
            }
        } catch (e) {
            console.warn(`Could not read README at ${p}:`, e);
        }
    }

    return (
        <div className="min-h-screen bg-[#09090b] p-8">
            <div className="max-w-5xl mx-auto">
                {/* Header */}
                <div className="mb-8 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-blue-600/10 rounded-2xl flex items-center justify-center border border-blue-500/20">
                            <BookOpen className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-white">Documentation</h1>
                            <p className="text-slate-400">Platform architecture and setup guide</p>
                        </div>
                    </div>
                </div>

                {/* Markdown Content */}
                <div className="prose prose-invert prose-slate max-w-none">
                    <div className="bg-white/5 border border-white/10 rounded-3xl p-8">
                        <ReactMarkdown
                            components={{
                                h1: ({ node, ...props }) => <h1 className="text-4xl font-bold text-white mb-6 mt-8 first:mt-0" {...props} />,
                                h2: ({ node, ...props }) => <h2 className="text-3xl font-bold text-white mb-4 mt-8 pb-2 border-b border-white/10" {...props} />,
                                h3: ({ node, ...props }) => <h3 className="text-2xl font-semibold text-white mb-3 mt-6" {...props} />,
                                h4: ({ node, ...props }) => <h4 className="text-xl font-semibold text-slate-200 mb-2 mt-4" {...props} />,
                                p: ({ node, ...props }) => <p className="text-slate-300 mb-4 leading-relaxed" {...props} />,
                                ul: ({ node, ...props }) => <ul className="list-disc list-inside text-slate-300 mb-4 space-y-2" {...props} />,
                                ol: ({ node, ...props }) => <ol className="list-decimal list-inside text-slate-300 mb-4 space-y-2" {...props} />,
                                li: ({ node, ...props }) => <li className="text-slate-300" {...props} />,
                                code: ({ node, inline, ...props }: any) =>
                                    inline ? (
                                        <code className="bg-blue-600/20 text-blue-300 px-2 py-1 rounded text-sm font-mono" {...props} />
                                    ) : (
                                        <code className="block bg-[#0c0c0e] text-blue-100 p-4 rounded-xl overflow-x-auto text-sm font-mono mb-4" {...props} />
                                    ),
                                pre: ({ node, ...props }) => <pre className="bg-[#0c0c0e] rounded-xl overflow-hidden mb-4" {...props} />,
                                a: ({ node, ...props }) => <a className="text-blue-400 hover:text-blue-300 underline" {...props} />,
                                blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-blue-500 pl-4 italic text-slate-400 my-4" {...props} />,
                                table: ({ node, ...props }) => <table className="w-full border-collapse mb-4" {...props} />,
                                th: ({ node, ...props }) => <th className="border border-white/10 bg-white/5 px-4 py-2 text-left text-white font-semibold" {...props} />,
                                td: ({ node, ...props }) => <td className="border border-white/10 px-4 py-2 text-slate-300" {...props} />,
                                img: ({ node, ...props }) => <img className="rounded-xl my-4 max-w-full" {...props} />,
                            }}
                        >
                            {markdown}
                        </ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
}
