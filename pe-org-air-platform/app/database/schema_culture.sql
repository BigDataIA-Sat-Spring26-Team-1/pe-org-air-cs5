-- Glassdoor raw reviews table
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
);

-- Culture scores aggregated by ticker and date
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
);
