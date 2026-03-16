import asyncio
import os
from pathlib import Path
from typing import List, Optional, Set
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from sec_edgar_downloader import Downloader

from app.models.sec import FilingMetadata

logger = structlog.get_logger()

class SecDownloader:
    """
    Robust SEC Edgar Downloader with concurrency and rate limiting.
    Downloads 10-K, 10-Q, 8-K filings.
    """
    def __init__(self, download_dir: str, email: str, company: str, max_workers: int = 1):
        self.download_dir = Path(download_dir)
        self.downloader = Downloader(company, email, download_folder=str(self.download_dir))
        # max_workers kept for signature compatibility but ignored
        self.max_workers = 1 

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _download_safe(self, ticker: str, filing_type: str, limit: int = 1, after_date: Optional[str] = None):
        """
        Blocking download call wrapped with retry logic.
        """
        try:
            count = self.downloader.get(filing_type, ticker, limit=limit, after=after_date)
            return count
        except Exception as e:
            logger.error("download_failed", ticker=ticker, type=filing_type, error=str(e))
            raise e

    def download_ticker(self, ticker: str, filing_types: List[str], limit_per_type: int = 2) -> int:
        """
        Synchronous download for a single ticker. Ideal for Airflow tasks.
        """
        total = 0
        for f_type in filing_types:
            try:
                count = self._download_safe(ticker, f_type, limit=limit_per_type)
                total += count
            except Exception:
                # Logged in _download_safe, continue to next type
                continue
        return total

    async def download_filings(self, tickers: List[str], filing_types: List[str], limit_per_type: int = 2) -> List[FilingMetadata]:
        """
        Async wrapper for backward compatibility. 
        Previously ran in parallel threads, now runs sequentially since Airflow/Orchestrator handles concurrency.
        """
        logger.info("starting_batch_download", tickers_count=len(tickers))
        
        for ticker in tickers:
            self.download_ticker(ticker, filing_types, limit_per_type)
        
        # Scan directory to gather metadata of downloaded files
        return self._scan_downloaded_files(tickers)

    def _scan_downloaded_files(self, tickers: List[str]) -> List[FilingMetadata]:
        """
        Scans the download directory to discover what was actually downloaded.
        Returns a list of metadata objects.
        """
        discovered = []
        base_dir = self.download_dir / "sec-edgar-filings"
        
        if not base_dir.exists():
            return []

        for ticker in tickers:
            ticker_dir = base_dir / ticker
            if not ticker_dir.exists():
                continue
            
            for f_type_dir in ticker_dir.iterdir():
                if not f_type_dir.is_dir(): continue
                filing_type = f_type_dir.name
                
                for accession_dir in f_type_dir.iterdir():
                    if not accession_dir.is_dir(): continue
                    accession_number = accession_dir.name
                    
                    candidates = list(accession_dir.glob("*.*"))
                    
                    # Prioritize HTML for parsing, but keep track of what we have
                    primary_file = next((f for f in candidates if f.suffix == '.html'), None)
                    if not primary_file:
                        primary_file = next((f for f in candidates if f.suffix == '.txt'), None)
                    
                    if primary_file:
                        # Use the CIK from the parent directory if possible, fallback to ticker
                        # The sec-edgar-downloader might name the folder by ticker or CIK
                        # We want the official CIK if we can get it
                        meta = FilingMetadata(
                            ticker=ticker,
                            cik=ticker, 
                            company_name=ticker, 
                            filing_type=filing_type,
                            accession_number=accession_number,
                            s3_path="", 
                            content_hash="PENDING_" + accession_number 
                        )
                        discovered.append(meta)
                        
        return discovered
