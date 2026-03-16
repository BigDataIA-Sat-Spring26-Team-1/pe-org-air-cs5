import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Collector services
from .job_collector import JobCollector
from .patent_collector import PatentCollector
from .tech_stack_collector import TechStackCollector
from .leadership_collector import LeadershipCollector

# Data models
from .models import SignalCategory, ExternalSignal, CompanySignalSummary

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """
    Coordinates multi-source data collection and aggregates signals into 
    AI readiness scores. Outputs are validated against Pydantic models.
    """

    # Scoring weights for composite calculation
    WEIGHTS = {
        SignalCategory.TECHNOLOGY_HIRING: 0.30,
        SignalCategory.INNOVATION_ACTIVITY: 0.25,
        SignalCategory.DIGITAL_PRESENCE: 0.25,
        SignalCategory.LEADERSHIP_SIGNALS: 0.20
    }

    def __init__(self, bq_project: Optional[str] = None):
        self.job_service = JobCollector()
        self.patent_service = PatentCollector(project_id=bq_project)
        self.tech_service = TechStackCollector()
        self.leadership_service = LeadershipCollector()

    def _get_stable_id(self, ticker: str) -> str:
        """Generates a consistent UUID based on the ticker symbol."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, ticker.upper()))

    async def execute(self, company_name: str, ticker: str) -> Dict[str, Any]:
        """
        Runs the full analysis suite for a company. Returns a payload 
        compatible with the Snowflake 'Summary' and 'Signals' tables.
        """
        company_id_str = self._get_stable_id(ticker)
        company_id = uuid.UUID(company_id_str)
        
        logger.info(f"--- Launching comprehensive AI audit for {company_name} [{ticker}] ---")

        # 1. Foundation: Job postings are used as discovery for other pipes
        job_result = await asyncio.to_thread(self.job_service.collect, company_name)
        
        # 2. Strategy: Execute independent collectors in parallel
        patent_task = asyncio.to_thread(self.patent_service.collect, company_name)
        tech_task = self.tech_service.collect(company_name)
        leadership_task = self.leadership_service.collect(company_name)

        patent_result, tech_result, leadership_result = await asyncio.gather(
            patent_task, tech_task, leadership_task
        )

        # 3. Create validated ExternalSignal objects
        # These map directly to the 'external_signals' Snowflake table
        signals = [
            ExternalSignal(
                company_id=company_id,
                category=SignalCategory.TECHNOLOGY_HIRING,
                source="linkedin",
                signal_date=datetime.now(timezone.utc).date(),
                raw_value=job_result.raw_value,
                normalized_score=job_result.normalized_score,
                confidence=job_result.confidence,
                metadata=job_result.metadata
            ),
            ExternalSignal(
                company_id=company_id,
                category=SignalCategory.INNOVATION_ACTIVITY,
                source="google_patents",
                signal_date=datetime.now(timezone.utc).date(),
                raw_value=patent_result.raw_value,
                normalized_score=patent_result.normalized_score,
                confidence=patent_result.confidence,
                metadata=patent_result.metadata
            ),
            ExternalSignal(
                company_id=company_id,
                category=SignalCategory.DIGITAL_PRESENCE,
                source="builtwith",
                signal_date=datetime.now(timezone.utc).date(),
                raw_value=tech_result.raw_value,
                normalized_score=tech_result.normalized_score,
                confidence=tech_result.confidence,
                metadata=tech_result.metadata
            ),
            ExternalSignal(
                company_id=company_id,
                category=SignalCategory.LEADERSHIP_SIGNALS,
                source="web_search",
                signal_date=datetime.now(timezone.utc).date(),
                raw_value=leadership_result.raw_value,
                normalized_score=leadership_result.normalized_score,
                confidence=leadership_result.confidence,
                metadata=leadership_result.metadata
            )
        ]

        # 4. Generate validated CompanySignalSummary
        # This maps to the 'company_signal_summaries' Snowflake table
        composite = sum(s.normalized_score * self.WEIGHTS[s.category] for s in signals)

        summary = CompanySignalSummary(
            company_id=company_id,
            ticker=ticker.upper(),
            technology_hiring_score=signals[0].normalized_score,
            innovation_activity_score=signals[1].normalized_score,
            digital_presence_score=signals[2].normalized_score,
            leadership_signals_score=signals[3].normalized_score,
            composite_score=round(composite, 2),
            signal_count=len(signals),
            last_updated=datetime.now(timezone.utc)
        )

        logger.info(f"--- Analysis complete for {ticker}: Composite Score {summary.composite_score} ---")
        
        return {
            "summary": summary.model_dump(),
            "signals": [s.model_dump() for s in signals]
        }

if __name__ == "__main__":
    # Internal test execution
    import json
    
    async def run_test():
        orc = PipelineOrchestrator(bq_project="gen-lang-client-0720834968")
        result = await orc.execute("Caterpillar Inc.", "CAT")
        print("\nValidated Summary Object:")
        print(json.dumps(result["summary"], indent=2, default=str))

    asyncio.run(run_test())
