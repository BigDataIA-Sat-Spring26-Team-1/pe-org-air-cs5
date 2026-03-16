import asyncio
import json
import logging
from typing import Dict, Any, List

# Import both orchestrators
from pipelines.orchestrator import PipelineOrchestrator as OriginalOrchestrator
from pipelines_v2.orchestrator import MasterPipeline as V2Orchestrator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

async def compare_pipelines(company_name: str, ticker: str, categories: List[str] = None):
    logger.info(f"\n{'='*60}\nCOMPARING PIPELINES FOR: {company_name} ({ticker})\n{'='*60}")
    
    # Initialize both
    original = OriginalOrchestrator(bq_project="gen-lang-client-0720834968")
    v2 = V2Orchestrator(bq_project="gen-lang-client-0720834968")
    
    logger.info(f"Running Original Pipeline (Focused: {categories or 'All'})...")
    orig_res = await original.execute(company_name, ticker)
    
    logger.info(f"Running V2 Pipeline (Focused: {categories or 'All'})...")
    v2_res = await v2.run(company_name, ticker)
    
    # Compare Summary Scores
    print("\n--- SCORE COMPARISON ---")
    orig_sum = orig_res["summary"]
    v2_sum = v2_res["summary"]
    
    metrics = [
        "technology_hiring_score",
        "innovation_activity_score",
        "digital_presence_score",
        "leadership_signals_score",
        "composite_score"
    ]
    
    print(f"{'Metric':<30} | {'Original':<10} | {'V2':<10} | {'Diff':<10}")
    print("-" * 65)
    for m in metrics:
        o_val = orig_sum.get(m, 0)
        v_val = v2_sum.get(m, 0)
        diff = v_val - o_val
        print(f"{m:<30} | {o_val:<10.2f} | {v_val:<10.2f} | {diff:<10.2f}")

    # Log Evidence Counts
    print("\n--- EVIDENCE COMPARISON ---")
    def get_signal_meta(res, category):
        for s in res["signals"]:
            if s["category"] == category:
                return s.get("metadata", {})
        return {}
    
    print(f"{'Evidence Category':<30} | {'Original Count':<15} | {'V2 Count':<15}")
    print("-" * 65)
    
    # Technology Hiring
    orig_jobs = get_signal_meta(orig_res, "technology_hiring").get("tech_count", 0)
    v2_jobs = len(get_signal_meta(v2_res, "technology_hiring").get("job_evidence", []))
    print(f"{'Jobs Found':<30} | {orig_jobs:<15} | {v2_jobs:<15}")

    # Innovation Activity (Patents)
    orig_patents = get_signal_meta(orig_res, "innovation_activity").get("ai_count", 0)
    v2_patents = get_signal_meta(v2_res, "innovation_activity").get("total_ai_patents", 0)
    print(f"{'AI Patents Detected':<30} | {orig_patents:<15} | {v2_patents:<15}")

    # Digital Presence (Tech Markers)
    orig_meta_tech = get_signal_meta(orig_res, "digital_presence")
    orig_tech = orig_meta_tech.get("count", 0)
    v2_meta_tech = get_signal_meta(v2_res, "digital_presence")
    v2_tech = v2_meta_tech.get("count", 0)
    print(f"{'Tech Markers':<30} | {orig_tech:<15} | {v2_tech:<15}")
    print(f"  > Original Stack: {orig_meta_tech.get('stack', [])}")
    print(f"  > V2 Stack: {v2_meta_tech.get('technologies_found', [])}")

    # Leadership
    orig_meta_lead = get_signal_meta(orig_res, "leadership_signals")
    orig_lead = orig_meta_lead.get("signals_count", 0)
    v2_meta_lead = get_signal_meta(v2_res, "leadership_signals")
    v2_lead = v2_meta_lead.get("signals_count", 0)
    print(f"{'Leadership Indicators':<30} | {orig_lead:<15} | {v2_lead:<15}")
    print(f"  > Original Roles: {[h.get('role') for h in orig_meta_lead.get('leadership_evidence', [])]}")
    print(f"  > V2 Roles: {[h.get('role') for h in v2_meta_lead.get('leadership_evidence', [])]}")

async def main():
    companies = [
        {"name": "Caterpillar Inc.", "ticker": "CAT"}
    ]
    
    for comp in companies:
        await compare_pipelines(comp["name"], comp["ticker"])

if __name__ == "__main__":
    asyncio.run(main())
