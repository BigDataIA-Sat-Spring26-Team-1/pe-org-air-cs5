import asyncio
import logging
import argparse
import sys
import os
import pandas as pd
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Import models
from models import SignalCategory, SignalSource, ExternalSignal, CompanySignalSummary

# Import individual pipelines
from job_pipeline import JobPipeline
from tech_stack_pipeline import TechStackCollector
from patent_pipeline_v3 import PatentSignalV3
from leadership_pipeline import LeadershipSignalCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler("master_pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Canonical Company Mapping
COMPANY_REPORTS = [
    {"ticker": "CAT", "name": "Caterpillar Inc."},
    {"ticker": "DE",  "name": "Deere & Company"},
    {"ticker": "UNH", "name": "UnitedHealth Group"},
    {"ticker": "HCA", "name": "HCA Healthcare"},
    {"ticker": "ADP", "name": "Automatic Data Processing"},
    {"ticker": "PAYX", "name": "Paychex Inc."},
    {"ticker": "WMT", "name": "Walmart Inc."},
    {"ticker": "TGT", "name": "Target Corporation"},
    {"ticker": "JPM", "name": "JPMorgan Chase"},
    {"ticker": "GS",  "name": "Goldman Sachs"}
]

class MasterPipeline:
    def __init__(self):
        self.job_pipeline = JobPipeline()
        self.tech_stack_pipeline = TechStackCollector()
        self.patent_pipeline = PatentSignalV3(project_id="gen-lang-client-0720834968")
        self.leadership_pipeline = LeadershipSignalCollector()
        self.results = {}

    def resolve_company(self, target: str) -> tuple[str, str]:
        """Resolves a ticker or name to (Canonical Name, Canonical Ticker)."""
        target_clean = target.strip().upper()
        # 1. Try ticker match
        for c in COMPANY_REPORTS:
            if c['ticker'] == target_clean:
                return c['name'], c['ticker']
        # 2. Try name match
        for c in COMPANY_REPORTS:
            if c['name'].upper() == target_clean:
                return c['name'], c['ticker']
        # 3. Fallback (Use input as name and upper as ticker)
        return target, target_clean

    def get_company_id(self, company_name: str) -> uuid.UUID:
        """Generate a deterministic UUID for a company name."""
        return uuid.uuid5(uuid.NAMESPACE_DNS, company_name.lower().replace(" ", ""))

    async def run_all(self, target: str, days: int):
        # Resolve identity
        company_name, ticker = self.resolve_company(target)
        company_id = self.get_company_id(company_name)
        
        start_time = datetime.now(timezone.utc)
        logging.info(f"==================================================")
        logging.info(f"STARTING EXTERNAL SIGNALS PIPELINE")
        logging.info(f"Company: {company_name}")
        logging.info(f"Ticker:  {ticker}")
        logging.info(f"ID:      {company_id}")
        logging.info(f"==================================================")
        
        signals = []
        
        try:
            # Stage 1: FOUNDATION (Jobs + Patents)
            logging.info(f"--- Stage 1: Foundation ---")
            job_task = asyncio.to_thread(self.job_pipeline.process_jobs, company_name, days)
            patent_task = asyncio.to_thread(self.patent_pipeline.run, company_name)
            
            job_res, patent_res = await asyncio.gather(job_task, patent_task)
            
            # Record Job Signal
            signals.append(ExternalSignal(
                company_id=company_id,
                category=SignalCategory.TECHNOLOGY_HIRING,
                source=SignalSource.LINKEDIN,
                signal_date=datetime.now(timezone.utc),
                raw_value=f"{job_res.get('ai_job_count', 0)} AI jobs out of {job_res.get('total_tech_count', 0)} tech jobs",
                normalized_score=job_res.get('score', 1.0),
                confidence=job_res.get('confidence', 0.8),
                metadata=job_res
            ))

            # Record Patent Signal
            signals.append(ExternalSignal(
                company_id=company_id,
                category=SignalCategory.INNOVATION_ACTIVITY,
                source=SignalSource.USPTO,
                signal_date=datetime.now(timezone.utc),
                raw_value=f"{patent_res.get('identified_ai_patents', 0)} AI patents out of {patent_res.get('total_company_patents', 0)} total",
                normalized_score=patent_res.get('normalized_score', 0),
                confidence=1.0, # High confidence from official registry
                metadata=patent_res
            ))
            
            await asyncio.sleep(2) # Jitter

            # Stage 2: DEEP ANALYSIS (Tech Stack + Leadership)
            logging.info(f"--- Stage 2: Analysis ---")
            tech_task = self.tech_stack_pipeline.run(company_name)
            leadership_task = self.leadership_pipeline.run(company_name)
            
            tech_res, leadership_res = await asyncio.gather(tech_task, leadership_task)
            
            # Record Tech Stack Signal
            signals.append(ExternalSignal(
                company_id=company_id,
                category=SignalCategory.DIGITAL_PRESENCE,
                source=SignalSource.BUILTWITH,
                signal_date=datetime.now(timezone.utc),
                raw_value=f"{len(tech_res.get('ai_tech_detected', '').split(','))} AI technologies detected",
                normalized_score=tech_res.get('tech_stack_score', 0),
                confidence=0.85,
                metadata=tech_res
            ))

            # Record Leadership Signal
            signals.append(ExternalSignal(
                company_id=company_id,
                category=SignalCategory.LEADERSHIP_SIGNALS,
                source=SignalSource.PRESS_RELEASE,
                signal_date=datetime.now(timezone.utc),
                raw_value=f"{leadership_res.get('leadership_count', 0)} leaders identified",
                normalized_score=leadership_res.get('leadership_score', 0),
                confidence=leadership_res.get('confidence', 0.8),
                metadata=leadership_res
            ))

            # Final Aggregation
            summary = CompanySignalSummary(
                company_id=company_id,
                ticker=ticker,
                technology_hiring_score=next(s.normalized_score for s in signals if s.category == SignalCategory.TECHNOLOGY_HIRING),
                innovation_activity_score=next(s.normalized_score for s in signals if s.category == SignalCategory.INNOVATION_ACTIVITY),
                digital_presence_score=next(s.normalized_score for s in signals if s.category == SignalCategory.DIGITAL_PRESENCE),
                leadership_signals_score=next(s.normalized_score for s in signals if s.category == SignalCategory.LEADERSHIP_SIGNALS),
                signal_count=len(signals),
                last_updated=datetime.now(timezone.utc)
            )

            logging.info(f"==================================================")
            logging.info(f"FINAL COMPOSITE SCORE: {summary.composite_score:.2f}/100")
            logging.info(f"==================================================")

            # Persist Summary
            summary_file = "company_summaries.csv"
            summary_df = pd.DataFrame([summary.model_dump()])
            if os.path.exists(summary_file):
                history = pd.read_csv(summary_file)
                # Update if exists, else append
                history = history[history['ticker'] != ticker]
                pd.concat([history, summary_df], ignore_index=True).to_csv(summary_file, index=False)
            else:
                summary_df.to_csv(summary_file, index=False)

            # Persist Raw Signals
            signals_file = "raw_signals.csv"
            signals_df = pd.DataFrame([s.model_dump() for s in signals])
            # Convert JSON metadata to string for CSV
            signals_df['metadata'] = signals_df['metadata'].apply(json.dumps)
            if os.path.exists(signals_file):
                pd.concat([pd.read_csv(signals_file), signals_df], ignore_index=True).to_csv(signals_file, index=False)
            else:
                signals_df.to_csv(signals_file, index=False)

        except Exception as e:
            logging.error(f"Pipeline failed for {company_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import random
    
    parser = argparse.ArgumentParser(description="Master External Signals Pipeline")
    parser.add_argument("--company", required=True, help="Company Name or Ticker (e.g., CAT, UNH, 'John Deere')")
    parser.add_argument("--days", type=int, default=7, help="Number of days for job posting search")
    
    args = parser.parse_args()
    
    master = MasterPipeline()
    asyncio.run(master.run_all(args.company, args.days))
