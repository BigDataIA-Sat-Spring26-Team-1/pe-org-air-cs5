-- Industries table
CREATE TABLE IF NOT EXISTS industries (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    sector VARCHAR(100) NOT NULL,
    h_r_base DECIMAL(5, 2),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(10),
    industry_id VARCHAR(36) REFERENCES industries(id),
    position_factor DECIMAL(4, 3) DEFAULT 0.0,
    cik VARCHAR(20),
    name_norm VARCHAR(255),
    is_deleted BOOLEAN DEFAULT FALSE,
    market_cap_percentile FLOAT DEFAULT 0.5,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Assessments table
CREATE TABLE IF NOT EXISTS assessments (
    id VARCHAR(36) PRIMARY KEY,
    company_id VARCHAR(36) NOT NULL REFERENCES companies(id),
    assessment_type VARCHAR(20) NOT NULL,
    assessment_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    primary_assessor VARCHAR(255),
    secondary_assessor VARCHAR(255),
    v_r_score DECIMAL(5, 2),
    h_r_score DECIMAL(5, 2),
    synergy_score DECIMAL(5, 2),
    org_air_score DECIMAL(5, 2),
    confidence_score DECIMAL(5, 2),
    confidence_lower DECIMAL(5, 2),
    confidence_upper DECIMAL(5, 2),
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Dimension scores table
CREATE TABLE IF NOT EXISTS dimension_scores (
    id VARCHAR(36) PRIMARY KEY,
    assessment_id VARCHAR(36) NOT NULL REFERENCES assessments(id),
    dimension VARCHAR(30) NOT NULL,
    score DECIMAL(5, 2) NOT NULL,
    weight DECIMAL(4, 3),
    confidence DECIMAL(4, 3) DEFAULT 0.8,
    evidence_count INT DEFAULT 0,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    UNIQUE (assessment_id, dimension)
);

-- Migrations for existing tables
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS h_r_score DECIMAL(5, 2);
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS synergy_score DECIMAL(5, 2);
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS org_air_score DECIMAL(5, 2);
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(5, 2);