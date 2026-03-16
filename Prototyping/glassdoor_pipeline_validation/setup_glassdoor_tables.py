
import asyncio
import logging
import sys
from app.services.snowflake import db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Setting up Glassdoor Tables...")
    try:
        await db.connect()
        
        # 1. Glassdoor Reviews Table
        logger.info("Creating glassdoor_reviews table...")
        create_reviews_sql = """
        CREATE TABLE IF NOT EXISTS glassdoor_reviews (
            id STRING PRIMARY KEY,
            company_id STRING,
            ticker STRING,
            review_date TIMESTAMP,
            rating FLOAT,
            title STRING,
            pros STRING,
            cons STRING,
            advice_to_management STRING,
            is_current_employee BOOLEAN,
            job_title STRING,
            location STRING,
            culture_rating FLOAT,
            diversity_rating FLOAT,
            work_life_rating FLOAT,
            senior_management_rating FLOAT,
            comp_benefits_rating FLOAT,
            career_opp_rating FLOAT,
            recommend_to_friend STRING,
            ceo_rating STRING,
            business_outlook STRING,
            raw_json VARIANT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        await db.execute(create_reviews_sql)
        logger.info("glassdoor_reviews table created/verified.")

        # 2. Culture Scores Table
        logger.info("Creating culture_scores table...")
        create_scores_sql = """
        CREATE TABLE IF NOT EXISTS culture_scores (
            company_id STRING,
            ticker STRING,
            batch_date DATE,
            innovation_score FLOAT,
            data_driven_score FLOAT,
            ai_awareness_score FLOAT,
            change_readiness_score FLOAT,
            overall_sentiment FLOAT,
            review_count INTEGER,
            confidence_score FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
            PRIMARY KEY (company_id, batch_date)
        )
        """
        await db.execute(create_scores_sql)
        logger.info("culture_scores table created/verified.")

    except Exception as e:
        logger.error(f"Setup failed: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
