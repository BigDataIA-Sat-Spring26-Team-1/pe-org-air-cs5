-- External signals table for granular records
CREATE TABLE IF NOT EXISTS external_signals (
    id VARCHAR(36) PRIMARY KEY,
    signal_hash VARCHAR(64) UNIQUE, -- For deduplication logic
    company_id VARCHAR(36) NOT NULL REFERENCES companies(id),
    category VARCHAR(30) NOT NULL,
    source VARCHAR(30) NOT NULL,
    signal_date DATE NOT NULL,
    raw_value VARCHAR(500),
    normalized_score DECIMAL(5, 2),
    confidence DECIMAL(4, 3),
    metadata VARCHAR(5000), -- JSON stored as string
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- Company signal summary (Latest aggregated scores)
CREATE TABLE IF NOT EXISTS company_signal_summaries (
    company_id VARCHAR(36) PRIMARY KEY REFERENCES companies(id),
    ticker VARCHAR(10) NOT NULL,
    technology_hiring_score DECIMAL(5, 2) DEFAULT 0.0,
    innovation_activity_score DECIMAL(5, 2) DEFAULT 0.0,
    digital_presence_score DECIMAL(5, 2) DEFAULT 0.0,
    leadership_signals_score DECIMAL(5, 2) DEFAULT 0.0,
    composite_score DECIMAL(5, 2) DEFAULT 0.0,
    signal_count INT DEFAULT 0,
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);


-- Granular evidence items linked to specific signals
CREATE TABLE IF NOT EXISTS signal_evidence (
    id VARCHAR(36) PRIMARY KEY,
    signal_id VARCHAR(36) NOT NULL REFERENCES external_signals(id),
    company_id VARCHAR(36) NOT NULL REFERENCES companies(id),
    category VARCHAR(30) NOT NULL,
    source VARCHAR(30) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    url VARCHAR(1000),
    tags VARCHAR(1000), -- JSON array stored as string
    evidence_date DATE NOT NULL,
    metadata VARCHAR(5000), -- JSON stored as string
    indexed_in_cs4 BOOLEAN DEFAULT FALSE,
    indexed_at TIMESTAMP_NTZ,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Migration for existing environments
ALTER TABLE signal_evidence ADD COLUMN IF NOT EXISTS indexed_in_cs4 BOOLEAN DEFAULT FALSE;
ALTER TABLE signal_evidence ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMP_NTZ;