import asyncio
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import structlog
import pdfkit
from concurrent.futures import ProcessPoolExecutor

from app.pipelines.sec.downloader import SecDownloader
from app.pipelines.sec.parser import SecParser
from app.pipelines.sec.chunker import SemanticChunker
from app.models.registry import DocumentRegistry
from app.services.s3_storage import AWSService
from app.services.snowflake import db
from app.services.redis_cache import cache
from app.config import settings

logger = structlog.get_logger()

def process_filing_worker(meta, download_dir: str, known_hashes: set = None):
    """
    Process filing in a separate process (CPU-bound).
    """
    registry = DocumentRegistry(initial_hashes=known_hashes)
    parser = SecParser()
    chunker = SemanticChunker()
    aws = AWSService()
    
    results_chunk = {"processed": 0, "skipped": 0, "errors": 0, "doc_data": None}
    
    try:
        local_path = (
            Path(download_dir) / "sec-edgar-filings" / meta.cik / meta.filing_type / meta.accession_number
        )

        file_candidates = list(local_path.glob("*.*"))
        target_file = next((f for f in file_candidates if f.suffix.lower() in ['.html', '.pdf', '.txt']), None)

        if not target_file:
            return results_chunk

        # 1. Upload Raw File (Immediate)
        s3_raw_key = f"{settings.AWS_FOLDER}/{meta.cik}/{meta.filing_type}/{meta.accession_number}/{target_file.name}"
        try:
            if not aws.file_exists(s3_raw_key):
                aws.upload_file(str(target_file), s3_raw_key)
        except Exception: pass

        # 2. Parse Sections (Prioritize Data)
        sections = {}
        try:
            sections = parser.parse(target_file, form_type=meta.filing_type)
        except Exception as e:
            logger.warning("parsing_failed_partial_save", ticker=meta.ticker, accession=meta.accession_number, error=str(e))
        
        # 3. JSON Generation & Hash
        content_str = json.dumps(sections, sort_keys=True)
        # Ensure hash is unique to this specific filing even if empty
        hash_input = f"{content_str}_{meta.accession_number}_{meta.cik}"
        content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        if registry.is_processed(content_hash):
            results_chunk["skipped"] = 1
            return results_chunk

        # 4. Upload Parsed JSON (Only if we have content)
        s3_key = f"{settings.AWS_FOLDER}/{meta.cik}/{meta.filing_type}/{meta.accession_number}/parsed.json"
        if sections:
            try:
                aws.upload_bytes(content_str.encode("utf-8"), s3_key, "application/json")
            except Exception as e:
                logger.warning("json_upload_failed", error=str(e))

        # 5. Chunking
        all_chunks = []
        try:
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
        except Exception as e:
            logger.warning("chunking_failed", ticker=meta.ticker, error=str(e))

        doc_id = f"{meta.cik}_{meta.accession_number}"
        results_chunk["processed"] = 1
        results_chunk["doc_data"] = {
            "doc_id": doc_id,
            "meta": meta,
            "s3_key": s3_key,
            "content_hash": content_hash,
            "all_chunks": all_chunks
        }

        # 6. Best-effort PDF Generation (Last step, doesn't block data if it fails)
        if target_file.suffix.lower() in ['.html', '.htm', '.txt']:
            try:
                pdf_filename = target_file.stem + ".pdf"
                local_pdf_path = target_file.parent / pdf_filename
                s3_pdf_key = f"{settings.AWS_FOLDER}/{meta.cik}/{meta.filing_type}/{meta.accession_number}/{pdf_filename}"
                
                # Check file size (optimized limit 200MB)
                if target_file.stat().st_size <= 200 * 1024 * 1024:
                    temp_html_path = target_file.with_name(f"{target_file.stem}_clean.html")
                    try:
                        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Extract main document text
                        html_content = content
                        if "<SEC-DOCUMENT>" in content or "<DOCUMENT>" in content:
                            ftype = re.escape(meta.filing_type)
                            pattern = re.compile(r'<DOCUMENT>.*?>\s*<TYPE>.*?' + ftype + r'.*?<TEXT>(.*?)</TEXT>', re.DOTALL | re.IGNORECASE)
                            match = pattern.search(content)
                            if match:
                                html_content = match.group(1).strip()
                            else:
                                match_any = re.search(r'<TEXT>(.*?)</TEXT>', content, re.DOTALL | re.IGNORECASE)
                                if match_any:
                                    html_content = match_any.group(1).strip()

                        # Strip heavy Base64 content to prevent hangs
                        html_content = re.sub(r'<img[^>]+src=["\']data:image/[^"\']+["\'][^>]*>', '<!-- [Image Removed] -->', html_content, flags=re.IGNORECASE)
                        html_content = re.sub(r'<graphic>.*?</graphic>', '<!-- [Graphic Removed] -->', html_content, flags=re.DOTALL | re.IGNORECASE)

                        if "<html>" not in html_content.lower():
                             html_content = f"<html><body><pre>{html_content}</pre></body></html>"
                        
                        with open(temp_html_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)

                        if not local_pdf_path.exists():
                            options = {
                                'page-size': 'A4',
                                'margin-top': '0.75in',
                                'margin-right': '0.75in',
                                'margin-bottom': '0.75in',
                                'margin-left': '0.75in',
                                'encoding': "UTF-8",
                                'no-outline': None,
                                'enable-local-file-access': None,
                                'quiet': '',
                            }
                            pdfkit.from_file(str(temp_html_path), str(local_pdf_path), options=options)
                        
                        if local_pdf_path.exists() and local_pdf_path.stat().st_size > 1024:
                             aws.upload_file(str(local_pdf_path), s3_pdf_key)
                    except Exception as e:
                        logger.warning("pdfkit_gen_failed", file=target_file.name, error=str(e))
                    finally:
                        if temp_html_path.exists():
                            try: temp_html_path.unlink()
                            except: pass
                else:
                    logger.warning("pdf_gen_skipped_massive_file", file=target_file.name, size=target_file.stat().st_size)
            except Exception:
                pass

        return results_chunk

    except Exception as e:
        results_chunk["errors"] = 1
        results_chunk["error_msg"] = str(e)
        return results_chunk


class SecPipeline:
    def __init__(self, download_dir: str = "./data/sec_downloads"):
        self.download_dir = download_dir
        self.downloader = SecDownloader(
            download_dir=download_dir,
            email="admin@pe-orgair.com",
            company="PE OrgAIR"
        )
        self.registry = DocumentRegistry()
        # Use ProcessPoolExecutor for CPU-bound tasks (Parsing, PDF Gen)
        # Max workers = 4 to match likely vCPU count and avoid OOM
        self.pool = ProcessPoolExecutor(max_workers=4)

    async def run(self, tickers: List[str], limit: int = 2):
        logger.info("pipeline_start", tickers=tickers)

        # 1. Download filings (I/O bound, uses asyncio internally)
        metadatas = await self.downloader.download_filings(
            tickers=tickers,
            filing_types=["10-K", "10-Q", "8-K", "DEF 14A"],
            limit_per_type=limit
        )

        logger.info("download_complete", count=len(metadatas))

        results = {
            "processed": 0,
            "skipped": 0,
            "errors": 0
        }

        if not metadatas:
            return results

        loop = asyncio.get_event_loop()
        
        # 2. Schedule Processing in Process Pool
        tasks = []
        for meta in metadatas:
            # Offload to separate process
            task = loop.run_in_executor(
                self.pool, 
                process_filing_worker, 
                meta, 
                self.download_dir,
                self.registry.known_hashes
            )
            tasks.append(task)

        # 3. Process results ALIVE as they finish
        # This ensures that even if one file hangs or fails, others are saved immediately.
        for completed_task in asyncio.as_completed(tasks):
            try:
                # 2.5-minute timeout per file to prevent entire company backfill from hanging
                res = await asyncio.wait_for(completed_task, timeout=150)
                
                if isinstance(res, Exception):
                    logger.error("task_execution_failed", error=str(res))
                    results["errors"] += 1
                    continue
                
                if res.get("errors"):
                    logger.error("worker_processing_error", error=res.get("error_msg"))
                    results["errors"] += 1
                    continue

                doc_data = res.get("doc_data")
                if doc_data:
                    try:
                        await self._save_to_db(doc_data)
                        results["processed"] += 1
                    except Exception as e:
                        logger.error("db_save_failed", error=str(e))
                        results["errors"] += 1
                elif res.get("skipped"):
                    results["skipped"] += 1
                
            except Exception as e:
                logger.error("task_stream_error", error=str(e))
                results["errors"] += 1

        logger.info("pipeline_complete", results=results)
        return results

    async def _save_to_db(self, doc_data):
        doc_id = doc_data["doc_id"]
        meta = doc_data["meta"]
        content_hash = doc_data["content_hash"]
        all_chunks = doc_data["all_chunks"]

        # Use service helpers
        await db.create_sec_document(doc_data)

        chunk_params = []
        full_text = ""
        for ch in all_chunks:
            chunk_id = f"{doc_id}_{ch['index']}"
            chunk_params.append((
                chunk_id, doc_id, ch['index'],
                ch['section'], ch['text'], ch['tokens']
            ))
            full_text += f"\n {ch['text']}"

        if chunk_params:
            await db.create_sec_document_chunks_bulk(chunk_params)
        
        self.registry.add(content_hash)
        
        # Invalidate cache for this document so API sees latest status
        cache.delete(f"sec:doc:{doc_id}")
        # Invalidate 1st page of lists to show new doc
        cache.delete_pattern("sec:docs:*:*:50:0")

    def __del__(self):
        # Shutdown pool
        self.pool.shutdown(wait=False)
