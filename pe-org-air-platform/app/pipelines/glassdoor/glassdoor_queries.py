MERGE_GLASSDOOR_REVIEWS = """
MERGE INTO glassdoor_reviews AS target
USING (SELECT 
    %s AS id, %s AS company_id, %s AS ticker, %s AS review_date, %s AS rating, 
    %s AS title, %s AS pros, %s AS cons, %s AS advice_to_management, 
    %s AS is_current_employee, %s AS job_title, %s AS location, 
    %s AS culture_rating, %s AS diversity_rating, %s AS work_life_rating, 
    %s AS senior_management_rating, %s AS comp_benefits_rating, 
    %s AS career_opp_rating, %s AS recommend_to_friend, %s AS ceo_rating, 
    %s AS business_outlook, PARSE_JSON(%s) AS raw_json
) AS source
ON target.id = source.id
WHEN MATCHED THEN UPDATE SET
    company_id = source.company_id, ticker = source.ticker, review_date = source.review_date, rating = source.rating,
    title = source.title, pros = source.pros, cons = source.cons, advice_to_management = source.advice_to_management,
    is_current_employee = source.is_current_employee, job_title = source.job_title, location = source.location,
    culture_rating = source.culture_rating, diversity_rating = source.diversity_rating, work_life_rating = source.work_life_rating,
    senior_management_rating = source.senior_management_rating, comp_benefits_rating = source.comp_benefits_rating,
    career_opp_rating = source.career_opp_rating, recommend_to_friend = source.recommend_to_friend,
    ceo_rating = source.ceo_rating, business_outlook = source.business_outlook, raw_json = source.raw_json
WHEN NOT MATCHED THEN INSERT (
    id, company_id, ticker, review_date, rating, title, pros, cons, advice_to_management,
    is_current_employee, job_title, location, culture_rating, diversity_rating, work_life_rating,
    senior_management_rating, comp_benefits_rating, career_opp_rating, recommend_to_friend,
    ceo_rating, business_outlook, raw_json
) VALUES (
    source.id, source.company_id, source.ticker, source.review_date, source.rating, source.title, source.pros, source.cons, source.advice_to_management,
    source.is_current_employee, source.job_title, source.location, source.culture_rating, source.diversity_rating, source.work_life_rating,
    source.senior_management_rating, source.comp_benefits_rating, source.career_opp_rating, source.recommend_to_friend,
    source.ceo_rating, source.business_outlook, source.raw_json
)
"""

INSERT_CULTURE_SIGNAL = """
MERGE INTO culture_scores AS target
USING (SELECT 
    %s AS company_id, %s AS ticker, %s AS batch_date, 
    %s AS innovation_score, %s AS data_driven_score, %s AS ai_awareness_score, 
    %s AS change_readiness_score, %s AS overall_sentiment, %s AS review_count, 
    %s AS avg_rating, %s AS current_employee_ratio,
    PARSE_JSON(%s) AS positive_keywords_found, PARSE_JSON(%s) AS negative_keywords_found,
    %s AS confidence
) AS source
ON target.company_id = source.company_id AND target.batch_date = source.batch_date
WHEN MATCHED THEN UPDATE SET
    ticker = source.ticker,
    innovation_score = source.innovation_score,
    data_driven_score = source.data_driven_score,
    ai_awareness_score = source.ai_awareness_score,
    change_readiness_score = source.change_readiness_score,
    overall_sentiment = source.overall_sentiment,
    review_count = source.review_count,
    avg_rating = source.avg_rating,
    current_employee_ratio = source.current_employee_ratio,
    positive_keywords_found = source.positive_keywords_found,
    negative_keywords_found = source.negative_keywords_found,
    confidence = source.confidence,
    updated_at = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN INSERT (
    company_id, ticker, batch_date, innovation_score, data_driven_score, 
    ai_awareness_score, change_readiness_score, overall_sentiment, 
    review_count, avg_rating, current_employee_ratio, 
    positive_keywords_found, negative_keywords_found,
    confidence, created_at, updated_at
) VALUES (
    source.company_id, source.ticker, source.batch_date, source.innovation_score, source.data_driven_score, 
    source.ai_awareness_score, source.change_readiness_score, source.overall_sentiment, 
    source.review_count, source.avg_rating, source.current_employee_ratio,
    source.positive_keywords_found, source.negative_keywords_found,
    source.confidence, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
"""

CREATE_GLASSDOOR_REVIEWS_TABLE = """
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

CREATE_CULTURE_SCORES_TABLE = """
CREATE TABLE IF NOT EXISTS culture_scores (
    company_id STRING,
    ticker STRING,
    batch_date DATE,
    innovation_score NUMBER(10, 2),
    data_driven_score NUMBER(10, 2),
    ai_awareness_score NUMBER(10, 2),
    change_readiness_score NUMBER(10, 2),
    overall_sentiment NUMBER(10, 2),
    review_count INTEGER,
    avg_rating NUMBER(10, 2),
    current_employee_ratio NUMBER(10, 2),
    positive_keywords_found VARIANT,
    negative_keywords_found VARIANT,
    confidence NUMBER(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (company_id, batch_date)
)
"""
