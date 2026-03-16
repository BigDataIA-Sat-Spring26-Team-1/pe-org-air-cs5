import asyncio
import random
import logging
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Set, Dict, Optional
import os
import re
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class TechnologyDetection:
    name: str
    category: str
    is_ai_related: bool
    confidence: float

class TechStackCollector:
    """Integrated Technology Stack Collector (Jobs Data -> Domain Discovery -> Web Scan)."""

    AI_TECHNOLOGIES = {
        "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai", "azure machine learning", "amazon sagemaker", "google ml engine"],
        "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx", "jax", "flax", "xgboost", "lightgbm", "catboost", "detectron2", "opencv"],
        "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift", "athena", "presto", "dremio", "teradata", "cloudera", "confluent"],
        "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain", "mistral", "llama-index", "gradio", "streamlit", "pinecone", "weaviate", "milvus", "qdrant"]
    }

    def __init__(self, output_file="tech_stack_signals.csv", jobs_file="processed_jobs.csv"):
        self.output_file = output_file
        self.jobs_file = jobs_file
        self.stealth_config = Stealth()

    def get_domain_from_jobs(self, company_name: str) -> Optional[str]:
        """Try to extract company domain from existing job data."""
        if not os.path.exists(self.jobs_file):
            return None
            
        logging.info(f"Looking for '{company_name}' domain in {self.jobs_file}...")
        df = pd.read_csv(self.jobs_file)
        
        # Filter jobs for this company (case-insensitive)
        # Use a more flexible regex match
        mask = df['company'].fillna('').str.contains(company_name.split()[0], case=False, na=False)
        company_jobs = df[mask]
        
        if company_jobs.empty:
            return None

        # Logic 1: Check 'company_url' if it exists (some job boards provide the direct site)
        if 'company_url' in company_jobs.columns:
            urls = company_jobs['company_url'].dropna().unique()
            for url in urls:
                domain = urlparse(url).netloc
                # Blacklist generic platforms that might appear as company links
                if domain and not any(x in domain for x in ["linkedin.com", "greenhouse.io", "workday.com", "lever.co", "facebook.com", "twitter.com", "instagram.com"]):
                    return domain.replace('www.', '')

        # Logic 2: Search job descriptions for website mentions
        # Usually found at the end: "Visit us at www.tesla.com"
        for desc in company_jobs['description'].dropna().head(10):
            urls = re.findall(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-z]{2,})', desc)
            for d in urls:
                if company_name.lower().replace(" ", "") in d.lower():
                    return d

        return None

    async def find_domain_fallback(self, company_name: str) -> str:
        """Fallback search for domain if jobs data fails."""
        logging.info(f"Jobs search failed. Falling back to web search for '{company_name}'...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                # Simplify query for cleaner results
                clean_name = re.sub(r'[^\w\s]', '', company_name)
                await page.goto(f"https://www.google.com/search?q={clean_name}+official+website")
                cite = await page.query_selector("cite")
                if cite:
                    domain = (await cite.inner_text()).split(" › ")[0]
                    domain = re.sub(r'https?://(www\.)?', '', domain).split('/')[0].strip('.')
                    domain = re.sub(r'\.{2,}', '.', domain)
                    # Specific cleanup for companies like Deere
                    if "deere" in domain: domain = "deere.com"
                    await browser.close()
                    return domain
            except:
                pass
            await browser.close()
            
        # Better naive fallback: Try using the first meaningful word
        # e.g., "Paychex Inc." -> "paychex.com"
        # "Automatic Data Processing" -> "adp.com" (Hard to guess, but short is better)
        
        if company_name in ["ADP", "Automatic Data Processing"]:
            # Special logic for simple ticker-like names
             return "adp.com"

        # Logic 3: Check usage of company_url from jobs if available (rare but possible)
        # Note: This is covered in find_domain_from_jobs via 'company_url' column check

        # Clean name: "Paychex Inc." -> "paychex"
        simple_name = company_name.split()[0].lower().replace(",", "").replace(".", "")
        return f"{simple_name}.com"

        # Clean name: "Paychex Inc." -> "paychex"
        simple_name = company_name.split()[0].lower().replace(",", "").replace(".", "")
        return f"{simple_name}.com"

    async def get_tech_stack(self, domain: str) -> List[TechnologyDetection]:
        """Combined check: BuiltWith + Wappalyzer-style Header/Body Signatures."""
        detections = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await self.stealth_config.apply_stealth_async(page)
            
            try:
                # 1. BuiltWith Check
                logging.info(f"Scanning BuiltWith for signatures...")
                await page.goto(f"https://builtwith.com/{domain}", timeout=60000)
                await asyncio.sleep(3)
                content = (await page.inner_text("body")).lower()
                
                # 2. Add Wappalyzer-style Fingerprinting directly on the domain
                # (We check for script tags and meta data)
                # 2. Add Wappalyzer-style Fingerprinting directly on the domain
                logging.info(f"Performing Wappalyzer-style fingerprinting on {domain}...")
                
                # Robust Navigation with Fallbacks
                targets = [f"https://{domain}", f"https://www.{domain}", f"http://{domain}"]
                site_content = ""
                
                for target in targets:
                    try:
                        await page.goto(target, timeout=20000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        site_content = (await page.content()).lower()
                        logging.info(f"Successfully scanned {target}")
                        break
                    except Exception as e:
                        logging.warning(f"Failed to scan {target}: {e}")
                        continue
                
                combined_content = content + " " + site_content

                # General Tech Signatures (Common high-value tech)
                GENERAL_TECH = {
                    "frontend": ["react", "angular", "vue", "next.js", "typescript"],
                    "backend": ["node.js", "golang", "ruby on rails", "django", "spring boot"],
                    "infra": ["kubernetes", "docker", "terraform", "ansible", "nginx"],
                    "analytics": ["google analytics", "mixpanel", "segment", "amplitude"],
                    "crm": ["salesforce", "hubspot", "zendesk"]
                }

                # Match AI Tech
                for cat, techs in self.AI_TECHNOLOGIES.items():
                    for tech in techs:
                        if tech in combined_content:
                            detections.append(TechnologyDetection(
                                name=tech.upper(),
                                category=cat,
                                is_ai_related=True,
                                confidence=0.85
                            ))
                
                # Match General Tech
                for cat, techs in GENERAL_TECH.items():
                    for tech in techs:
                        if tech in combined_content:
                            detections.append(TechnologyDetection(
                                name=tech.upper(),
                                category=cat,
                                is_ai_related=False,
                                confidence=0.75
                            ))
            except Exception as e:
                logging.warning(f"Technical scan partially failed: {e}")
            
            await browser.close()
        return detections

    def get_internal_tech_from_jobs(self, company_name: str) -> List[TechnologyDetection]:
        """Harvest internal frameworks mentioned in descriptions (Pure Dynamic Evidence)."""
        detections = []
        if os.path.exists(self.jobs_file):
            df = pd.read_csv(self.jobs_file)
            mask = df['company'].fillna('').str.contains(company_name, case=False, na=False)
            company_jobs = df[mask]
            
            if not company_jobs.empty:
                all_text = " ".join(company_jobs['description'].fillna("")).lower()
                for cat, techs in self.AI_TECHNOLOGIES.items():
                    for tech in techs:
                        if tech in all_text:
                            detections.append(TechnologyDetection(
                                name=tech.upper(),
                                category=cat,
                                is_ai_related=True,
                                confidence=0.95
                            ))
        return detections

    async def run(self, company_name: str):
        # Step 1: Intelligent Domain Discovery
        domain = self.get_domain_from_jobs(company_name)
        if not domain:
            domain = await self.find_domain_fallback(company_name)
        
        logging.info(f"Domain for {company_name} identified as: {domain}")
        
        # Step 2: External Fingerprinting (Web)
        web_techs = await self.get_tech_stack(domain)
        
        # Step 3: Internal Fingerprinting (Jobs)
        job_techs = self.get_internal_tech_from_jobs(company_name)
        
        # Combine and Deduplicate
        all_detections = {t.name: t for t in (web_techs + job_techs)}.values()
        
        # Scoring Logic (Max 100)
        ai_techs = [t for t in all_detections if t.is_ai_related]
        categories = set(t.category for t in ai_techs)
        score = min(len(ai_techs) * 10, 50) + min(len(categories) * 12.5, 50)
        
        signal = {
            "company_name": company_name,
            "domain": domain,
            "tech_stack_score": score,
            "ai_tech_detected": ",".join([t.name for t in ai_techs]),
            "categories": ",".join(categories),
            "evidence_count": len(all_detections)
        }
        
        logging.info(f"Analysis Complete: Score {score}/100. Technologies: {signal['ai_tech_detected']}")
        
        # Persistence
        df_signal = pd.DataFrame([signal])
        if os.path.exists(self.output_file):
            history = pd.read_csv(self.output_file)
            pd.concat([history, df_signal], ignore_index=True).to_csv(self.output_file, index=False)
        else:
            df_signal.to_csv(self.output_file, index=False)
            
        # Save detailed metadata
        detailed_file = "detailed_tech_stack.csv"
        detailed_data = []
        for t in all_detections:
            detailed_data.append({
                "company": company_name,
                "technology": t.name,
                "category": t.category,
                "is_ai_related": t.is_ai_related,
                "confidence": t.confidence,
                "discovery_date": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            })
            
        if detailed_data:
            df_detailed = pd.DataFrame(detailed_data)
            if os.path.exists(detailed_file):
                history = pd.read_csv(detailed_file)
                # Avoid duplicates for same company and tech on same day
                mask = (history['company'] == company_name) & (history['technology'].isin(df_detailed['technology'])) & (history['discovery_date'] == datetime.now(timezone.utc).strftime("%Y-%m-%d"))
                df_detailed = df_detailed[~df_detailed['technology'].isin(history[history['company'] == company_name]['technology'])]
                if not df_detailed.empty:
                    pd.concat([history, df_detailed], ignore_index=True).to_csv(detailed_file, index=False)
            else:
                df_detailed.to_csv(detailed_file, index=False)
            logging.info(f"Saved {len(detailed_data)} tech stack details to {detailed_file}")
            
        return signal

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    
    collector = TechStackCollector()
    asyncio.run(collector.run(args.company))
