from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class SecDocument(BaseModel):
    document_id: str
    cik: str
    company_name: str
    filing_type: str
    accession_number: str
    s3_raw_path: Optional[str] = None
    content_hash: Optional[str] = None
    processing_status: str = "PENDING"
    created_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "0000018230_23_000011",
                "cik": "0000018230",
                "company_name": "CATERPILLAR INC",
                "filing_type": "10-K",
                "accession_number": "0000018230-23-000011",
                "s3_raw_path": "sec/0000018230/10-K/0000018230-23-000011/raw.html",
                "content_hash": "a1b2c3d4...",
                "processing_status": "COMPLETED",
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }

class SecDocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    section_name: Optional[str] = None
    chunk_text: str
    token_count: Optional[int] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "chunk_id": "0000018230_23_000011_0",
                "document_id": "0000018230_23_000011",
                "chunk_index": 0,
                "section_name": "Item 1. Business",
                "chunk_text": "Caterpillar Inc. is the world's leading manufacturer of construction and mining equipment...",
                "token_count": 120,
                "embedding": [0.1, 0.2, 0.3],
                "created_at": "2026-02-06T00:00:00"
            }
        }
    }

class SecCollectRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=1, description="List of tickers to collect filings for")
    company_name: Optional[str] = Field(None, description="Optional company name for validation")
    limit: int = Field(2, ge=1, le=10, description="Max filings per ticker")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tickers": ["CAT", "DE"],
                "company_name": "Caterpillar Inc.",
                "limit": 5
            }
        }
    }

class FilingMetadata(BaseModel):
    ticker: str
    cik: str
    company_name: str
    filing_type: str
    accession_number: str
    filing_date: Optional[str] = None
    report_period: Optional[str] = None
    s3_path: str
    content_hash: str
    
class ProcessedChunk(BaseModel):
    chunk_index: int
    text: str
    tokens: int
    section: str 
    embedding: Optional[List[float]] = None

class PipelineStats(BaseModel):
    files_downloaded: int = 0
    files_parsed: int = 0
    chunks_generated: int = 0
    errors: List[str] = []
