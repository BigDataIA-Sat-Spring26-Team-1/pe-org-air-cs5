import asyncio
import logging
import pandas as pd
import os
import re
import random
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from .models import CollectorResult

# Configure logger
logger = logging.getLogger(__name__)

class LeadershipCollector:
    """
    Evaluates corporate AI commitment by identifying senior leadership roles 
    and specialized AI-centric executive appointments.
    """

    LEADERSHIP_KEYWORDS = [
        "chief ai officer", "caio", "chief artificial intelligence officer",
        "vp of ai", "vice president of artificial intelligence",
        "director of ai", "head of ai", "director of machine learning",
        "head of data science", "chief data scientist", "chief ai scientist",
        "chief data and ai officer", "caido", "vp of generative ai",
        "vp of machine learning", "vp of ai transformation", "head of autonomy"
    ]

    def __init__(self, jobs_file: str = "processed_jobs.csv"):
        self.jobs_file = jobs_file
        self.stealth_config = Stealth()

    def _assess_rank(self, title: str) -> str:
        """Categorizes an organizational title into a seniority tier."""
        t = title.lower()
        if any(x in t for x in ["chief", "president", "caio", "caido"]): return "STRATEGIC"
        if any(x in t for x in ["vp", "vice president", "evp", "svp", "managing director"]): return "OPERATIONAL"
        if any(x in t for x in ["director", "head", "gm", "general manager"]): return "MANAGEMENT"
        return "SPECIALIST"

    def _find_internal_signals(self, company: str) -> List[Dict[str, Any]]:
        """Scans job files for hiring vacancies or reporting line mentions."""
        results = []
        if not os.path.exists(self.jobs_file):
            return results

        try:
            df = pd.read_csv(self.jobs_file)
            # Use a more flexible search for company name
            name_parts = company.split()
            search_name = name_parts[0] if name_parts else company
            
            mask = df['company'].fillna('').str.contains(search_name, case=False)
            company_data = df[mask]
            
            for _, row in company_data.iterrows():
                title = str(row.get('title', '')).lower()
                desc = str(row.get('description', '')).lower()
                
                # 1. Senior AI vacancies
                if any(role_kw in title for role_kw in ["director", "head", "vp", "chief"]):
                    if any(ai_kw in title for ai_kw in ["ai", "ml", "data science", "machine learning"]):
                        results.append({
                            "type": "recruitment",
                            "title": row.get('title'),
                            "tier": self._assess_rank(title)
                        })
                
                # 2. Reporting lines
                reporting_patterns = [
                    r"(?:reports|reporting) to the (head of ai|caio|vp of machine learning|director of data science|chief data and ai officer)",
                    r"work closely with our (head of ai|caio|vp of generative ai|chief technology officer)"
                ]
                for pattern in reporting_patterns:
                    match = re.search(pattern, desc)
                    if match:
                        results.append({
                            "type": "structure",
                            "title": match.group(1).upper(),
                            "tier": self._assess_rank(match.group(1))
                        })
        except Exception:
            pass
            
        return results

    async def _find_external_signals(self, company: str) -> List[Dict[str, Any]]:
        """Browses for news regarding leadership updates using robust dynamic discovery."""
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = await context.new_page()
            await self.stealth_config.apply_stealth_async(page)
            
            # Match queries from the working leadership_pipeline.py
            queries = [
                f'"{company}" (appointed OR joined OR named) ({ "|".join(self.LEADERSHIP_KEYWORDS[:5]) })',
                f'{company} "Head of AI" news',
                f'{company} "Chief AI Officer" 2024..2025'
            ]
            
            for query in queries:
                try:
                    await page.goto(f"https://www.google.com/search?q={query.replace(' ', '+')}", timeout=20000)
                    await asyncio.sleep(2)
                    
                    dom_data = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('h3')).map(h3 => {
                            const container = h3.closest('div.g') || h3.parentElement.parentElement;
                            return { title: h3.innerText, snippet: container ? container.innerText : "" };
                        });
                    }""")
                    
                    if not dom_data:
                        body_text = await page.inner_text("body")
                        dom_data = [{"title": "Raw results", "snippet": body_text}]

                    for item in dom_data:
                        text = f"{item['title']} {item['snippet']}".lower()
                        for role in self.LEADERSHIP_KEYWORDS:
                            if re.search(role, text, re.IGNORECASE):
                                results.append({
                                    "type": "appointment",
                                    "title": role.upper(),
                                    "tier": self._assess_rank(role),
                                    "context": item['title']
                                })
                                break
                    await asyncio.sleep(random.uniform(2, 4))
                except Exception:
                    continue
            await browser.close()
        return results

    async def collect(self, company: str) -> CollectorResult:
        """Evaluates overall leadership commitment and calculates a score."""
        logger.info(f"Checking management commitment for {company}")
        
        internal_hits = self._find_internal_signals(company)
        external_hits = await self._find_external_signals(company)
        
        all_signals = internal_hits + external_hits
        
        # Scoring by Tier Presence
        tiers_detected = set(s["tier"] for s in all_signals)
        score = 0
        if "STRATEGIC" in tiers_detected: score += 60
        elif "OPERATIONAL" in tiers_detected: score += 45
        elif "MANAGEMENT" in tiers_detected: score += 30
        
        bonus = min(len(all_signals) * 8, 40)
        final_score = min(score + bonus, 100)
        
        return CollectorResult(
            normalized_score=float(final_score),
            confidence=0.85 if all_signals else 0.5,
            raw_value=f"Identified {len(all_signals)} specialized leadership markers",
            metadata={
                "signals_count": len(all_signals),
                "tiers": list(tiers_detected)
            }
        )
