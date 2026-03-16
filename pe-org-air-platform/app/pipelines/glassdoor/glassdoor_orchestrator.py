import logging
import json
from datetime import datetime, date
from typing import List, Dict

from app.services.s3_storage import aws_service
from app.services.snowflake import db
from app.pipelines.glassdoor.glassdoor_collector import GlassdoorCultureCollector, COMPANY_IDS
from app.pipelines.glassdoor.glassdoor_queries import MERGE_GLASSDOOR_REVIEWS, INSERT_CULTURE_SIGNAL, CREATE_GLASSDOOR_REVIEWS_TABLE, CREATE_CULTURE_SCORES_TABLE
from app.models.glassdoor_models import GlassdoorReview, CultureSignal

logger = logging.getLogger(__name__)

class GlassdoorOrchestrator:
    def __init__(self):
        self.collector = GlassdoorCultureCollector()

    async def save_reviews_to_snowflake(self, reviews: List[GlassdoorReview]):
        """
        Bulk insert parsed reviews into Snowflake.
        """
        if not reviews:
            return

        # Prepare list of tuples for SQL insert
        values = []
        for r in reviews:
            values.append((
                r.id,
                r.company_id,
                r.ticker,
                r.review_date,
                r.rating,
                r.title,
                r.pros[:4000] if r.pros else None,
                r.cons[:4000] if r.cons else None,
                r.advice_to_management[:4000] if r.advice_to_management else None,
                r.is_current_employee,
                r.job_title,
                r.location,
                r.culture_rating,
                r.diversity_rating,
                r.work_life_rating,
                r.senior_management_rating,
                r.comp_benefits_rating,
                r.career_opp_rating,
                r.recommend_to_friend,
                r.ceo_rating,
                r.business_outlook,
                json.dumps(r.raw_json)
            ))
        
        logger.debug(f"Prepared {len(values)} records for Snowflake upsert.")
        
        for val in values:
            await db.execute(MERGE_GLASSDOOR_REVIEWS, val)
            
        logger.info(f"Upserted {len(reviews)} reviews to Snowflake.")

    async def save_culture_signal(self, signal: CultureSignal):
        if not signal:
            return
            
        logger.info(f"Saving culture signal for {signal.ticker} to Snowflake...")
        try:
            await db.execute(
                INSERT_CULTURE_SIGNAL,
                (
                    signal.company_id,
                    signal.ticker,
                    signal.batch_date,
                    signal.innovation_score,
                    signal.data_driven_score,
                    signal.ai_awareness_score,
                    signal.change_readiness_score,
                    signal.overall_sentiment,
                    signal.review_count,
                    signal.avg_rating,
                    signal.current_employee_ratio,
                    json.dumps(signal.positive_keywords_found),
                    json.dumps(signal.negative_keywords_found),
                    signal.confidence
                )
            )
            logger.info("Successfully saved culture signal.")
        except Exception as e:
            logger.error(f"Failed to save culture signal: {e}")

    async def initialize_tables(self):
        """
        Ensure Snowflake tables exist before running the pipeline.
        """
        try:
            await db.execute(CREATE_GLASSDOOR_REVIEWS_TABLE)
            await db.execute(CREATE_CULTURE_SCORES_TABLE)
            logger.info("Verified/Created Glassdoor tables in Snowflake.")
        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")

    async def run_pipeline(self, ticker: str, glassdoor_id: str = None, limit: int = 20, force_refresh: bool = False) -> Dict[str, int]:
        # 0. Ensure tables exist
        await self.initialize_tables()

        # Resolve ID first
        if not glassdoor_id:
            glassdoor_id = COMPANY_IDS.get(ticker)
        else:
            # Inject custom ID into COMPANY_IDS so fetch_reviews can find it
            COMPANY_IDS[ticker] = glassdoor_id
        
        if not glassdoor_id:
            logger.error(f"Cannot run pipeline for {ticker}: No Glassdoor ID found.")
            return {"reviews": 0, "signals": 0}

        # 1. Fetch & Parse (internal caching handled)
        parsed_reviews = await self.collector.fetch_reviews(ticker, limit=limit)
        
        if not parsed_reviews:
            logger.info(f"No reviews found for {ticker}")
            return {"reviews": 0, "signals": 0}

        company_id = parsed_reviews[0].company_id if parsed_reviews else None
            
        # 2. Save raw reviews to Snowflake
        await self.save_reviews_to_snowflake(parsed_reviews)

        # 3. Analyze and compute aggregated culture signal → write to culture_scores
        culture_signal = None
        if company_id:
            culture_signal = self.collector.analyze_reviews(company_id, ticker, parsed_reviews)
            if culture_signal:
                await self.save_culture_signal(culture_signal)
                logger.info(f"Culture signal saved for {ticker}")
        
        return {"reviews": len(parsed_reviews), "signals": 1 if culture_signal else 0}

    async def run_batch(self, companies: List[Dict[str, str]], limit: int = 20, force_refresh: bool = False):
        """
        Run pipeline for multiple companies.
        Expects a list of dicts: [{"ticker": "NVDA", "id": "7633"}, ...]
        """
        logger.info(f"Starting batch run for {len(companies)} companies...")
        for comp in companies:
            ticker = comp.get("ticker")
            gid = comp.get("id")
            if ticker:
                await self.run_pipeline(ticker, glassdoor_id=gid, limit=limit, force_refresh=force_refresh)
