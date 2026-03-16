import logging
import asyncio
import random
import re
from typing import List, Dict, Any, Set
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from .utils import WebUtils
from .models import CollectorResult, SignalCategory

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
        self.stealth_config = Stealth()

    async def _resolve_domain(self, company: str) -> str:
        """Determines the company's official web domain using job data and fallbacks."""
        import os
        from urllib.parse import urlparse
        
        # 1. Check local jobs cache
        if os.path.exists(self.jobs_file):
            try:
                df = pd.read_csv(self.jobs_file)
                if 'company' in df.columns:
                    mask = df['company'].fillna('').str.contains(company.split()[0], case=False, na=False)
                    company_jobs = df[mask]
                    
                    if not company_jobs.empty:
                        # Logic to extract URL from description if explicit url missing
                        for desc in company_jobs['description'].dropna().head(10):
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
            await self.stealth_config.apply_stealth_async(page)
            
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

    def _analyze_job_mentions(self, company: str) -> List[Dict[str, str]]:
        """Harvest internal tech mentions from job descriptions."""
        import os
        import pandas as pd
        found = []
        if os.path.exists(self.jobs_file):
            try:
                df = pd.read_csv(self.jobs_file)
                if 'company' in df.columns:
                    mask = df['company'].fillna('').str.contains(company.split()[0], case=False)
                    combined_text = " ".join(df[mask]['description'].fillna("").astype(str)).lower()
                    
                    seen = set()
                    for cat, techs in self.TECH_INDICATORS.items():
                        for tech in techs:
                            if tech in combined_text and tech not in seen:
                                found.append({"name": tech.upper(), "category": cat, "source": "job_descriptions"})
                                seen.add(tech)
            except Exception as e:
                logger.debug(f"Job tech analysis failed: {e}")
        return found

    async def collect(self, company_name: str) -> CollectorResult:
        """Orchestrates technical footprint discovery and evaluation."""
        domain = await self._resolve_domain(company_name)
        logger.info(f"Analyzing technical stack for {company_name} via {domain}")
        
        web_task = self._scan_footprint(domain)
        # We run job analysis synchronously
        job_data = self._analyze_job_mentions(company_name)
        logger.info(f"Job description analysis found {len(job_data)} markers")
        
        web_data = await web_task
        logger.info(f"Web scan found {len(web_data)} markers")

        all_signals = {s["name"]: s for s in (web_data + job_data)}
        detections = list(all_signals.values())
        unique_cats = set(s["category"] for s in detections)
        
        # Scoring: Breadth (50) + Diversity (50)
        final_score = min(len(detections) * 10, 50) + min(len(unique_cats) * 12.5, 50)

        if not detections:
            return self._empty_result(f"No AI technical markers found for {company_name}")

        return CollectorResult(
            category=SignalCategory.DIGITAL_PRESENCE,
            normalized_score=round(float(final_score), 2),
            confidence=0.85,
            raw_value=f"Detected {len(detections)} AI signals across {len(unique_cats)} categories",
            source="Web & Job Data",
            metadata={
                "technologies_found": [d['name'] for d in detections],
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
