import logging
import os
import pandas as pd
import asyncio
import random
import re
from typing import List, Dict, Any, Set
from playwright.async_api import async_playwright
from datetime import datetime
from difflib import SequenceMatcher
from .utils import WebUtils, apply_stealth
from app.models.signals import CollectorResult, SignalCategory, SignalEvidenceItem

logger = logging.getLogger(__name__)

class TechStackCollector:
    """
    Assesses a company's technology infrastructure and AI tool adoption.
    """

    TECH_INDICATORS = {
        "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai", "azure machine learning", "amazon sagemaker", "google ml engine"],
        "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx", "jax", "flax", "xgboost", "lightgbm", "catboost", "detectron2", "opencv"],
        "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift", "athena", "presto", "dremio", "teradata", "cloudera", "confluent"],
        "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain", "mistral", "llama-index", "gradio", "streamlit", "pinecone", "weaviate", "milvus", "qdrant"]
    }

    def __init__(self, jobs_file: str = "processed_jobs.csv"):
        self.jobs_file = jobs_file

    async def _resolve_domain(self, company: str, ticker: str = None) -> str:
        """Determines the company's official web domain using job data and fallbacks."""
        from urllib.parse import urlparse
        
        # 1. Check local jobs cache
        if os.path.exists(self.jobs_file):
            try:
                df = pd.read_csv(self.jobs_file)
                if 'company' in df.columns:
                    # Use a list to collect results
                    matches = []
                    for _, row in df.iterrows():
                        listing_comp = str(row.get('company', '')).lower()
                        # Use a simpler match for domain resolution
                        if company.lower()[:5] in listing_comp or listing_comp in company.lower():
                            matches.append(row)
                    
                    if matches:
                        for row in matches[:10]:
                            desc = row.get('description', '')
                            if pd.isna(desc): continue
                            urls = re.findall(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-z]{2,})', str(desc))
                            for d in urls:
                                if company.split()[0].lower() in d.lower():
                                    return d
                
            except Exception:
                pass

        # 2. Automated fallback search
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                clean_name = re.sub(r'[^\w\s]', '', company)
                await page.goto(f"https://www.google.com/search?q={clean_name}+official+website")
                cite = await page.query_selector("cite")
                if cite:
                    domain = (await cite.inner_text()).split(" › ")[0]
                    domain = re.sub(r'https?://(www\.)?', '', domain).split('/')[0].strip('.')
                    await browser.close()
                    return domain
            except:
                pass
            await browser.close()

        return f"{company.split()[0].lower()}.com"

    async def _scan_footprint(self, domain: str) -> List[Dict[str, str]]:
        """Scans external platforms and the domain itself for signatures."""
        found = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await apply_stealth(page)
            
            try:
                # BuiltWith Scan
                await page.goto(f"https://builtwith.com/{domain}", timeout=30000)
                await asyncio.sleep(2)
                bw_content = (await page.inner_text("body")).lower()
                
                # Direct Site Scan (Wappalyzer style)
                site_content = ""
                targets = [f"https://{domain}", f"https://www.{domain}"]
                for t in targets:
                    try:
                        await page.goto(t, timeout=15000)
                        site_content = (await page.content()).lower()
                        break
                    except:
                        continue
                
                combined = bw_content + " " + site_content
                seen = set()
                for cat, techs in self.TECH_INDICATORS.items():
                    for tech in techs:
                        if tech in combined and tech not in seen:
                            found.append({"name": tech.upper(), "category": cat, "source": "web_scan"})
                            seen.add(tech)
            except Exception as e:
                logger.warning(f"Technical footprint scan for {domain} incomplete: {e}")
            finally:
                await browser.close()
        return found

    def _is_matching_company(self, listing_company: str, target_company: str, ticker: str = None) -> bool:
        """Robust check to ensure the job listing belongs to the target company."""
        if not listing_company:
            return False
            
        l_name = str(listing_company).lower().strip()
        t_name = str(target_company).lower().strip()
        
        # 1. Exact or partial name match
        if l_name in t_name or t_name in l_name:
            return True
            
        # 2. Ticker match
        if ticker and ticker.lower() in l_name.split():
            return True
            
        # 3. Alphanumeric normalization match (CRITICAL for JPMorganChase)
        l_norm = re.sub(r'[^a-z0-9]', '', l_name)
        t_norm = re.sub(r'[^a-z0-9]', '', t_name)
        if l_norm == t_norm or l_norm in t_norm or t_norm in l_norm:
            return True

        # 4. Sequence similarity ratio (Fuzzy match)
        similarity = SequenceMatcher(None, l_name, t_name).ratio()
        return similarity > 0.75

    async def _analyze_job_mentions(self, company: str, ticker: str = None, job_evidence: List[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Harvest internal tech mentions from job descriptions."""
        found = []
        combined_text = ""
        
        # 1. Use results from JobCollector if provided
        if job_evidence:
            combined_text = " ".join([j.get('description', '') for j in job_evidence]).lower()
        
        # 2. Fallback: Fetch from Snowflake if we have a db client
        else:
            try:
                from app.services.snowflake import db
                # Get company record to find its ID
                comp_rec = await db.fetch_company_by_ticker(ticker) if ticker else None
                if comp_rec:
                    job_descs = await db.fetch_job_descriptions_for_talent(comp_rec['id'])
                    combined_text = " ".join(job_descs).lower()
            except Exception as e:
                logger.error(f"Error fetching jobs from Snowflake for tech markers: {e}")

        if not combined_text:
            return []

        seen = set()
        for cat, techs in self.TECH_INDICATORS.items():
            for tech in techs:
                # Match with word boundaries to avoid false positives (e.g. "spark" in "sparkle")
                if re.search(rf"\b{re.escape(tech.lower())}\b", combined_text):
                    found.append({"name": tech.upper(), "category": cat, "source": "job_descriptions"})
                    seen.add(tech)
        return found

    async def collect(self, company_name: str, ticker: str = None, job_evidence: List[Dict[str, Any]] = None) -> CollectorResult:
        """Orchestrates technical footprint discovery and evaluation."""
        try:
            domain = await self._resolve_domain(company_name, ticker)
            logger.info(f"Analyzing technical stack for {company_name} via {domain}")
            
            web_task = self._scan_footprint(domain)
            # Use job_evidence if provided
            job_data = await self._analyze_job_mentions(company_name, ticker, job_evidence=job_evidence)
            logger.info(f"Job description analysis found {len(job_data)} markers")
            
            web_data = await web_task
            logger.info(f"Web scan found {len(web_data)} markers")
        except Exception as e:
            logger.error(f"Tech stack collection failed: {e}")
            return self._empty_result(f"Tech scan failed: {str(e)}")


        all_signals = {s["name"]: s for s in (web_data + job_data)}
        detections = list(all_signals.values())
        unique_cats = set(s["category"] for s in detections)
        
        # Scoring: Breadth (50) + Diversity (50)
        final_score = min(len(detections) * 10, 50) + min(len(unique_cats) * 12.5, 50)

        if not detections:
            return self._empty_result(f"No AI technical markers found for {company_name}")

        evidence_items = [
            SignalEvidenceItem(
                title=f"Tech Marker: {d['name']}",
                description=f"Infrastructure signal detected via {d['source']}",
                tags=[d['category'], "TechStack", "Infrastructure"],
                date=datetime.now().date().isoformat(),
                metadata={"tech": d['name'], "category": d['category'], "discovery_method": d['source']}
            )
            for d in detections
        ]

        return CollectorResult(
            category=SignalCategory.DIGITAL_PRESENCE,
            normalized_score=round(float(final_score), 2),
            confidence=0.85,
            raw_value=f"Detected {len(detections)} AI signals across {len(unique_cats)} categories",
            source="Web & Job Data Analysis",
            evidence=evidence_items,
            metadata={
                "domain_scanned": domain,
                "category_diversity": list(unique_cats),
                "count": len(detections)
            }
        )

    def _empty_result(self, msg: str) -> CollectorResult:
        return CollectorResult(
            category=SignalCategory.DIGITAL_PRESENCE,
            normalized_score=0,
            confidence=0.5,
            raw_value=msg,
            source="Web Scan"
        )
