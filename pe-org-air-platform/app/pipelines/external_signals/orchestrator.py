import asyncio
import logging
import uuid
from typing import Dict, List, Any
from datetime import datetime
from .job_collector import JobCollector
from .patent_collector import PatentCollector
from .tech_stack_collector import TechStackCollector
from .leadership_collector import LeadershipCollector
from app.models.signals import CompanySignalSummary, ExternalSignal, CollectorResult, SignalCategory, SignalEvidence

# Setup concise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class MasterPipeline:
    """Manages data collection from all signal sources."""

    def __init__(self):
        self.job_collector = JobCollector()
        self.patent_collector = PatentCollector()
        self.tech_collector = TechStackCollector()
        self.lead_collector = LeadershipCollector()

    async def run(self, company_name: str, ticker: str, company_id: str = None, job_days: int = 60, patent_years: int = 5) -> Dict[str, Any]:
        """Runs all collectors and prepares data for database."""
        if not company_id:
            company_id = str(uuid.uuid4())

        logger.info(f"--- Starting AI Audit for {company_name} ({ticker}) ---")

        # 1. Fetch job signals first (needed as input for tech stack analysis)
        job_res = await self.job_collector.collect(company_name, days=job_days, ticker=ticker)
        
        # 2. Extract job evidence/descriptions for tech stack analyzer
        job_docs = []
        if job_res and hasattr(job_res, "evidence"):
            for item in job_res.evidence:
                job_docs.append({"description": item.description})

        # 3. Parallel collection of other signals
        tasks = {
            "Innovation (Patents)": self.patent_collector.collect(company_name, years=patent_years, ticker=ticker),
            "Digital Presence (Tech Stack)": self.tech_collector.collect(company_name, ticker=ticker, job_evidence=job_docs),
            "Leadership Signals": self.lead_collector.collect(company_name, ticker=ticker)
        }
        
        names = list(tasks.keys())
        coroutines = list(tasks.values())

        other_results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        results = [job_res] + list(other_results)
        all_names = ["Hiring Intensity"] + names
        
        sanitized_results: List[CollectorResult] = []
        for name, r in zip(all_names, results):
            if isinstance(r, Exception):
                logger.error(f"Collector '{name}' failed: {r}", exc_info=True)
                continue
            sanitized_results.append(r)


        signals: List[Dict[str, Any]] = []
        all_evidence: List[Dict[str, Any]] = []
        
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
            signal_id = signal.id
            signals.append(signal.model_dump(mode='json'))
            
            for item in res.evidence:
                evidence = SignalEvidence(
                    signal_id=signal_id,
                    company_id=company_id,
                    category=res.category,
                    source=res.source,
                    title=item.title,
                    description=item.description,
                    url=item.url,
                    tags=item.tags,
                    evidence_date=item.date,
                    metadata=item.metadata
                )
                all_evidence.append(evidence.model_dump(mode='json'))

        # Aggregate summary scores
        summary_data = {
            "company_id": company_id,
            "ticker": ticker,
            "technology_hiring_score": 0.0,
            "innovation_activity_score": 0.0,
            "digital_presence_score": 0.0,
            "leadership_signals_score": 0.0,
            "composite_score": 0.0,
            "signal_count": len(signals)
        }

        for res in sanitized_results:
            if res.category == SignalCategory.TECHNOLOGY_HIRING:
                summary_data["technology_hiring_score"] = res.normalized_score
            elif res.category == SignalCategory.INNOVATION_ACTIVITY:
                summary_data["innovation_activity_score"] = res.normalized_score
            elif res.category == SignalCategory.DIGITAL_PRESENCE:
                summary_data["digital_presence_score"] = res.normalized_score
            elif res.category == SignalCategory.LEADERSHIP_SIGNALS:
                summary_data["leadership_signals_score"] = res.normalized_score

        # Calculate composite score (weighted average)
        weights = {
            "technology_hiring_score": 0.35,
            "innovation_activity_score": 0.25,
            "digital_presence_score": 0.20,
            "leadership_signals_score": 0.20
        }
        
        composite = 0.0
        for key, weight in weights.items():
            composite += summary_data[key] * weight
        
        summary_data["composite_score"] = round(composite, 2)

        return {
            "summary": summary_data,
            "signals": signals,
            "evidence": all_evidence
        }
