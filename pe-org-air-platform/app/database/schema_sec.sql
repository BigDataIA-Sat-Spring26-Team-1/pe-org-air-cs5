CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(255) PRIMARY KEY,
    cik VARCHAR(20) NOT NULL,
    company_name VARCHAR(255),
    filing_type VARCHAR(20),
    accession_number VARCHAR(255),
    filing_date DATE,
    s3_raw_path VARCHAR(500),
    content_hash VARCHAR(64),
    processing_status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    document_id VARCHAR(255) REFERENCES documents(document_id),
    chunk_index INTEGER,
    section_name VARCHAR(50),
    chunk_text TEXT,
    token_count INTEGER,
    embedding VECTOR(FLOAT, 1536), -- Assuming OpenAI embeddings
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
