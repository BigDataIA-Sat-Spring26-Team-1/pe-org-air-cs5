"use client";

import React from 'react';

// Match the CS4 ScoreJustification structure
export interface EvidenceSource {
    source_id: string;
    source_type: string;
    content: string;
    confidence: number;
    url?: string;
}

export interface ScoreJustification {
    dimension: string;
    score: number;
    level: number;
    level_name: string;
    evidence_strength: string;
    rubric_criteria: string;
    supporting_evidence: EvidenceSource[];
    gaps_identified: string[];
}

interface EvidenceDisplayProps {
    justification: ScoreJustification;
    isLoading?: boolean;
}

export default function EvidenceDisplay({ justification, isLoading = false }: EvidenceDisplayProps) {
    if (isLoading) {
        return (
            <div className="animate-pulse flex flex-col gap-4 p-6 bg-slate-900 border border-slate-800 rounded-xl">
                <div className="h-6 w-1/3 bg-slate-800 rounded"></div>
                <div className="h-4 w-1/2 bg-slate-800 rounded"></div>
                <div className="h-20 w-full bg-slate-800 rounded mt-4"></div>
            </div>
        );
    }

    // Determine badge color based on level
    const getLevelColor = (level: number) => {
        switch (level) {
            case 5: return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
            case 4: return "bg-green-500/10 text-green-400 border-green-500/20";
            case 3: return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
            case 2: return "bg-orange-500/10 text-orange-400 border-orange-500/20";
            case 1: return "bg-red-500/10 text-red-400 border-red-500/20";
            default: return "bg-slate-500/10 text-slate-400 border-slate-500/20";
        }
    };

    const getStrengthColor = (str: string) => {
        const s = str.toLowerCase();
        if (s.includes('high') || s.includes('strong')) return "text-emerald-400";
        if (s.includes('moderate') || s.includes('medium')) return "text-yellow-400";
        return "text-orange-400";
    };

    return (
        <div className="bg-[#0f1115] border border-slate-800 rounded-xl overflow-hidden shadow-xl">
            {/* Header Section */}
            <div className="border-b border-slate-800 p-6 bg-[#161920]">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-100 capitalize mb-1">
                            {justification.dimension.replace(/_/g, ' ')} Focus
                        </h2>
                        <div className="flex items-center gap-3">
                            <span className="text-slate-400 text-sm">
                                Score: <strong className="text-slate-200">{justification.score.toFixed(1)}/100</strong>
                            </span>
                            <span className="text-slate-600">•</span>
                            <span className="text-slate-400 text-sm">
                                Strength: <strong className={getStrengthColor(justification.evidence_strength)}>{justification.evidence_strength}</strong>
                            </span>
                        </div>
                    </div>

                    <div className={`px-4 py-1.5 rounded-full border text-sm font-semibold tracking-wide ${getLevelColor(justification.level)}`}>
                        L{justification.level} - {justification.level_name}
                    </div>
                </div>

                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 font-mono text-sm text-blue-200">
                    <strong>Rubric Criteria Hit:</strong> {justification.rubric_criteria}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
                {/* Evidence Column */}
                <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Supporting Evidence ({justification.supporting_evidence.length})
                    </h3>

                    <div className="space-y-4">
                        {justification.supporting_evidence.length === 0 ? (
                            <p className="text-slate-500 italic text-sm">No specific evidence found.</p>
                        ) : (
                            justification.supporting_evidence.map((ev, idx) => (
                                <div key={idx} className="bg-[#1a1d24] border border-slate-800 rounded-lg p-4 transition hover:border-slate-700">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded">
                                            {ev.source_type}
                                        </span>
                                        <span className="text-xs text-slate-500 font-mono">
                                            Conf: {(ev.confidence * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                    <p className="text-sm text-slate-300 leading-relaxed">"{ev.content}"</p>
                                    {ev.url && (
                                        <a href={ev.url} target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:text-blue-300 mt-3 inline-flex items-center gap-1">
                                            View Citation
                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                                        </a>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Gaps Column */}
                <div>
                    <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <svg className="w-4 h-4 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Identified Gaps ({justification.gaps_identified.length})
                    </h3>

                    <div className="space-y-3">
                        {justification.gaps_identified.length === 0 ? (
                            <p className="text-slate-500 italic text-sm">No critical gaps identified.</p>
                        ) : (
                            justification.gaps_identified.map((gap, idx) => (
                                <div key={idx} className="flex gap-3 bg-red-500/5 border border-red-500/10 rounded-lg p-3">
                                    <div className="mt-0.5 text-red-400">
                                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>
                                    </div>
                                    <span className="text-sm text-slate-300">{gap}</span>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
