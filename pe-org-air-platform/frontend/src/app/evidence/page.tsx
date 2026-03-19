"use client";

import React, { useState } from 'react';
import EvidenceDisplay, { ScoreJustification } from '@/components/EvidenceDisplay';

const mockData: ScoreJustification = {
    dimension: "data_infrastructure",
    score: 68.5,
    level: 3,
    level_name: "Developing",
    evidence_strength: "Moderate",
    rubric_criteria: "Has centralized data lakes but poor metadata management.",
    supporting_evidence: [
        {
            source_id: "sec-10k-2023",
            source_type: "SEC Filing",
            confidence: 0.95,
            content: "Company has heavily invested in migrating legacy ERP systems to Snowflake and AWS platforms in Q3.",
            url: "https://example.com/sec/10k"
        },
        {
            source_id: "job-post-012",
            source_type: "Job Posting",
            confidence: 0.88,
            content: "Hiring standard Data Engineers; requirements emphasize SQL and basic ETL over modern MLOps pipelines.",
            url: "https://example.com/jobs/012"
        }
    ],
    gaps_identified: [
        "No standardized data quality checks across downstream reporting.",
        "Data cataloging initiatives are mentioned but implementation details are missing."
    ]
};

export default function EvidencePage() {
    const [data, setData] = useState(mockData);
    const [loading, setLoading] = useState(false);

    const simulateFetch = () => {
        setLoading(true);
        setTimeout(() => setLoading(false), 800);
    };

    return (
        <div className="min-h-screen bg-[#09090b] text-slate-300 p-8 pt-20">
            <div className="max-w-4xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">CS5 Evidence UI Showcase</h1>
                        <p className="text-slate-500 text-sm">Task 9.5 Placeholder. Waiting for backend MCP integration.</p>
                    </div>

                    <button
                        onClick={simulateFetch}
                        className="bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg transition"
                    >
                        Refresh Mock Data
                    </button>
                </div>

                <EvidenceDisplay
                    justification={data}
                    isLoading={loading}
                />
            </div>
        </div>
    );
}
