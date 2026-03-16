
import asyncio
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------
# Atomic Tasks for Airflow (Pure Functions / Static Methods)
# ---------------------------------------------------------

async def fetch_ticker_list(source: str = "config") -> List[str]:
    """
    Task 1: Fetch list of tickers to process.
    Could fetch from Snowflake, a config file, or hardcoded list.
    """
    # Import inside function to avoid top-level load
    from app.services.snowflake import db
    
    if source == "snowflake":
        # Example: Fetch from a 'monitored_companies' table
        companies = await db.fetch_companies(limit=1000, offset=0)
        return [c['ticker'] for c in companies if c.get('ticker')]
    
    # Default / Config source
    return ["NVDA", "JPM", "WMT", "GE", "DG", "CAT", "DE", "UNH", "HCA", "ADP", "PAYX", "TGT", "GS"]

async def download_ticker_filings(
    ticker: str, 
    limit: int = 2, 
    filing_types: List[str] = ["10-K", "10-Q", "8-K", "DEF 14A"],
    download_dir: str = "/opt/airflow/app_code/data/sec_downloads"
) -> Dict[str, Any]:
    """
    Task 2 (Mapped): Download filings for a single ticker.
    Returns summary stats and path to downloaded files.
    """
    from app.pipelines.sec.downloader import SecDownloader
    
    downloader = SecDownloader(
        download_dir=download_dir,
        email="admin@pe-orgair.com",
        company="PE OrgAIR",
        max_workers=1 # Single worker per task instance since we map at ticker level
    )
    
    # Updated to use synchronous method
    downloader.download_ticker(ticker, filing_types, limit)
    
    # We can skip returning metadatas here since discovery happens in next task
    # But if we want stats:
    return {
        "ticker": ticker,
        "downloaded_count": "N/A - Check Discover Step", 
        "download_dir": download_dir
    }

def scan_and_discover_filings(
    download_dir: str = "/opt/airflow/app_code/data/sec_downloads"
) -> List[Dict[str, Any]]:
    """
    Task 3: Scan directory and return list of FilingMetadata dicts.
    This bridges the Download and Process phases.
    """
    from pathlib import Path
    
    base_dir = Path(download_dir) / "sec-edgar-filings"
    discovered = []
    
    if not base_dir.exists():
        return []

    for ticker_dir in base_dir.iterdir():
        if not ticker_dir.is_dir(): continue
        ticker = ticker_dir.name
        
        for f_type_dir in ticker_dir.iterdir():
            if not f_type_dir.is_dir(): continue
            filing_type = f_type_dir.name
            
            for accession_dir in f_type_dir.iterdir():
                if not accession_dir.is_dir(): continue
                accession_number = accession_dir.name
                
                candidates = list(accession_dir.glob("*.*"))
                primary_file = next((f for f in candidates if f.suffix == '.html'), None)
                if not primary_file:
                    primary_file = next((f for f in candidates if f.suffix == '.txt'), None)
                
                if primary_file:
                    meta = {
                        "cik": ticker, # Fallback, ideally from dir structure if available
                        "company_name": ticker,
                        "filing_type": filing_type,
                        "accession_number": accession_number,
                        "file_path": str(primary_file),
                        "file_name": primary_file.name
                    }
                    discovered.append(meta)
    
    return discovered

async def process_single_filing(
    filing_meta: Dict[str, Any],
    s3_force_upload: bool = False
) -> Dict[str, Any]:
    """
    Task 4 (Mapped): Process a single filing.
    Parse -> Hash -> Chunk -> S3 (Upload) -> Snowflake (Prep).
    Returns dict ready for DB insertion or status.
    """
    from app.pipelines.sec.parser import SecParser
    from app.pipelines.sec.chunker import SemanticChunker
    from app.services.s3_storage import AWSService
    from app.config import settings

    parser = SecParser()
    chunker = SemanticChunker()
    aws = AWSService()
    
    file_path = Path(filing_meta["file_path"])
    if not file_path.exists():
        return {"status": "skipped", "reason": "file_not_found", "meta": filing_meta}

    # 1. Upload Raw
    s3_raw_key = f"{settings.AWS_FOLDER}/{filing_meta['cik']}/{filing_meta['filing_type']}/{filing_meta['accession_number']}/{filing_meta['file_name']}"
    if s3_force_upload or not aws.file_exists(s3_raw_key):
        try:
            aws.upload_file(str(file_path), s3_raw_key)
        except Exception as e:
            logger.error("s3_upload_failed", error=str(e))

    # 2. Parse
    try:
        sections = parser.parse(file_path, form_type=filing_meta['filing_type'])
    except Exception as e:
        return {"status": "failed", "reason": "parsing_error", "error": str(e), "meta": filing_meta}

    # 3. Hash
    content_str = json.dumps(sections, sort_keys=True)
    hash_input = f"{content_str}_{filing_meta['accession_number']}_{filing_meta['cik']}"
    content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    # 5. Upload Parsed JSON
    s3_parsed_key = f"{settings.AWS_FOLDER}/{filing_meta['cik']}/{filing_meta['filing_type']}/{filing_meta['accession_number']}/parsed.json"
    if sections:
        try:
            aws.upload_bytes(content_str.encode("utf-8"), s3_parsed_key, "application/json")
        except Exception as e:
            logger.warning("json_upload_failed", error=str(e))

    # 6. Chunk
    all_chunks = []
    chunk_index_counter = 0
    for section_name, text in sections.items():
        chunks = chunker.chunk(text)
        for chunk_text in chunks:
            safe_text = chunk_text[:60000]
            all_chunks.append({
                "section": section_name,
                "text": safe_text, 
                "index": chunk_index_counter,
                "tokens": len(safe_text.split())
            })
            chunk_index_counter += 1

    doc_id = f"{filing_meta['cik']}_{filing_meta['accession_number']}"
    
    return {
        "status": "success",
        "doc_data": {
            "doc_id": doc_id,
            "meta": filing_meta,
            "s3_key": s3_parsed_key,
            "s3_raw_path": s3_raw_key,
            "content_hash": content_hash,
            "all_chunks": all_chunks
        }
    }

async def save_filing_to_db(doc_data: Dict[str, Any]):
    """
    Task 5: Save processed filing data to Snowflake.
    """
    if not doc_data: return
    
    from app.services.snowflake import db
    from app.models.sec import FilingMetadata
    
    meta = doc_data['meta']
    
    db_doc_data = {
        'doc_id': doc_data['doc_id'],
        'meta': FilingMetadata(
            cik=meta['cik'],
            company_name=meta['company_name'],
            filing_type=meta['filing_type'],
            accession_number=meta['accession_number'],
            s3_path=doc_data['s3_raw_path'],
            content_hash=doc_data['content_hash']
        ),
        's3_key': doc_data['s3_key'],
        'content_hash': doc_data['content_hash'],
        'all_chunks': doc_data['all_chunks']
    }
    
    await db.create_sec_document(db_doc_data)
    
    chunk_params = []
    for ch in doc_data['all_chunks']:
        chunk_id = f"{doc_data['doc_id']}_{ch['index']}"
        chunk_params.append((
            chunk_id, doc_data['doc_id'], ch['index'],
            ch['section'], ch['text'], ch['tokens']
        ))
    
    if chunk_params:
        await db.create_sec_document_chunks_bulk(chunk_params)


