
import pytest
from pathlib import Path
from app.pipelines.sec.downloader import SecDownloader

@pytest.mark.asyncio
async def test_sec_download_directory_creation(tmp_path):
    path = tmp_path / "downloads"
    d = SecDownloader(
        download_dir=str(path),
        email="test@example.com",
        company="TestCorp",
        max_workers=1
    )
    
    # Simple check for directory structure
    metas = await d.download_filings(
        tickers=["AAPL"],
        filing_types=["10-K"],
        limit_per_type=1
    )
    
    assert (path / "sec-edgar-filings").exists()
