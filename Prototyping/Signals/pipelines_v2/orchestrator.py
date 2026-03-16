import asyncio
import logging
import uuid
from typing import Dict, List, Any
from datetime import datetime
from .job_collector import JobCollector
from .patent_collector import PatentCollector
from .tech_stack_collector import TechStackCollector
from .leadership_collector import LeadershipCollector
from .models import CompanySignalSummary, ExternalSignal, CollectorResult, SignalCategory

# Setup concise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class MasterPipeline:
    """Orchestrates the end-to-end collection of AI readiness signals."""

    def __init__(self, bq_project: str):
        self.job_collector = JobCollector()
        self.patent_collector = PatentCollector(project_id=bq_project)
        self.tech_collector = TechStackCollector()
        self.lead_collector = LeadershipCollector()

    async def run(self, company_name: str, ticker: str, company_id: str = None) -> Dict[str, Any]:
        """
        Executes all collectors in parallel and prepares the data for Snowflake.
        
        Returns:
            A dictionary with:
            - summary: Data for the 'company_signal_summaries' table
            - signals: List of data for the 'external_signals' table (includes raw evidence)
        """
        if not company_id:
            company_id = str(uuid.uuid4())

        logger.info(f"--- Starting AI Audit for {company_name} ({ticker}) ---")

        # 1. Foundation: Job collection happens first as it provides data for other collectors
        job_res = await self.job_collector.collect(company_name)
        
        # 2. Strategy: Other collectors run in parallel
        other_tasks = [
            self.patent_collector.collect(company_name),
            self.tech_collector.collect(company_name),
            self.lead_collector.collect(company_name)
        ]

        # Use gather to run the rest concurrently
        other_results = await asyncio.gather(*other_tasks, return_exceptions=True)
        
        results = [job_res] + list(other_results)
        
        sanitized_results: List[CollectorResult] = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Collector task failed during execution: {r}")
                continue
            sanitized_results.append(r)

        # Map results to our ExternalSignal model for database storage
        signals: List[Dict[str, Any]] = []
        for res in sanitized_results:
            signal = ExternalSignal(
                company_id=company_id,
                category=res.category,
                source=res.source,
                signal_date=res.signal_date,
                raw_value=res.raw_value,
                normalized_score=res.normalized_score,
                confidence=res.confidence,
                metadata=res.metadata
            )
            signals.append(signal.dict())

        # Group data for the high-level summary table
        summary_data = {
            "company_id": company_id,
            "ticker": ticker,
            "technology_hiring_score": next((s.normalized_score for s in sanitized_results if s.category == SignalCategory.TECHNOLOGY_HIRING), 0.0),
            "innovation_activity_score": next((s.normalized_score for s in sanitized_results if s.category == SignalCategory.INNOVATION_ACTIVITY), 0.0),
            "digital_presence_score": next((s.normalized_score for s in sanitized_results if s.category == SignalCategory.DIGITAL_PRESENCE), 0.0),
            "leadership_signals_score": next((s.normalized_score for s in sanitized_results if s.category == SignalCategory.LEADERSHIP_SIGNALS), 0.0),
            "signal_count": len(sanitized_results)
        }

        # Core scoring weights for the composite AI readiness index
        weights = {
            "technology_hiring_score": 0.30,   # Hiring intensity
            "innovation_activity_score": 0.25, # Patent & R&D depth
            "digital_presence_score": 0.25,    # Technical stack footprint
            "leadership_signals_score": 0.20   # Executive commitment
        }
        
        composite = sum(summary_data[k] * w for k, w in weights.items())
        summary_data["composite_score"] = round(composite, 2)
        summary_data["last_updated"] = datetime.utcnow()

        summary = CompanySignalSummary(**summary_data)

        logger.info(f"Audit for {ticker} finished. Final Score: {summary.composite_score}")
        
        return {
            "summary": summary.dict(),
            "signals": signals
        }

# Example usage entry point
async def main():
    pipeline = MasterPipeline(bq_project="gen-lang-client-0720834968")
    result = await pipeline.run("Caterpillar Inc.", "CAT")
    
    # This structure is now ready to be pushed to Snowflake
    print(f"Summary: {result['summary']}")
    print(f"Number of detailed signals captured: {len(result['signals'])}")

if __name__ == "__main__":
    asyncio.run(main())
