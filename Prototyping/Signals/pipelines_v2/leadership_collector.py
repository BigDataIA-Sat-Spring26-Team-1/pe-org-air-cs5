import asyncio
import logging
import random
import re
from typing import List, Dict, Any
from .utils import WebUtils
from .models import CollectorResult, SignalCategory

logger = logging.getLogger(__name__)

class LeadershipCollector:
    """Tracks senior-level AI hires and organizational structural changes."""

    # Strategic AI roles and leadership indicators
    TARGET_ROLES = [
        "chief ai officer", "caio", "chief artificial intelligence officer",
        "vp of ai", "vice president of artificial intelligence",
        "director of ai", "head of ai", "director of machine learning",
        "head of data science", "chief data scientist", "chief ai scientist",
        "chief data and ai officer", "caido", "vp of generative ai",
        "vp of machine learning", "vp of ai transformation", "head of autonomy"
    ]

    def _assess_rank(self, title: str) -> str:
        """Categorizes an organizational title into a seniority tier."""
        t = title.lower()
        if any(x in t for x in ["chief", "president", "caio", "caido"]): return "STRATEGIC"
        if any(x in t for x in ["vp", "vice president", "evp", "svp", "managing director"]): return "OPERATIONAL"
        if any(x in t for x in ["director", "head", "gm", "general manager"]): return "MANAGEMENT"
        return "SPECIALIST"

    async def _search_public_records(self, company_name: str) -> List[Dict[str, str]]:
        """Scans for press releases and news about AI leadership changes."""
        clean_name = WebUtils.clean_company_name(company_name)
        
        # We use a variety of search patterns to ensure high coverage of public records
        queries = [
            f'"{clean_name}" (appointed OR joined OR named) ({ "|".join(self.TARGET_ROLES[:5]) })',
            f'{clean_name} "Head of AI" news',
            f'{clean_name} "Chief AI Officer" 2024..2025'
        ]
        
        detections = []
        for query in queries:
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            items = await WebUtils.get_page_items(search_url)
            
            for item in items:
                combined_text = f"{item['title']} {item['snippet']}".lower()
                for role in self.TARGET_ROLES:
                    if re.search(role, combined_text, re.IGNORECASE):
                        detections.append({
                            "role": role.upper(),
                            "tier": self._assess_rank(role),
                            "context": item['title'],
                            "source": "Public Records"
                        })
                        break # One detection per search result
        return detections

    def _find_internal_signals(self, company_name: str) -> List[Dict[str, str]]:
        """Scans local job evidence (if available) for leadership mentions."""
        import os
        import pandas as pd
        results = []
        jobs_file = "processed_jobs.csv" # Standard name used in v2
        
        if not os.path.exists(jobs_file):
            return results

        try:
            df = pd.read_csv(jobs_file)
            clean = company_name.split()[0].lower()
            for _, row in df.iterrows():
                title = str(row.get('title', '')).lower()
                desc = str(row.get('description', '')).lower()
                context = title + " " + desc
                
                # Look for senior AI vacancies with strict word boundaries
                seniority_pattern = r'\b(director|head|vp|chief|president|gm)\b'
                ai_pattern = r'\b(ai|ml|data science|machine learning|artificial intelligence)\b'
                
                if re.search(seniority_pattern, title) and re.search(ai_pattern, title):
                    results.append({
                        "role": title.upper(),
                        "tier": self._assess_rank(title),
                        "source": "Internal Recruitment"
                    })
        except Exception:
            pass
        return results

    async def collect(self, company_name: str) -> CollectorResult:
        """Identifies leadership indicators using both news and internal data."""
        logger.info(f"Scanning leadership structure for {company_name}")
        
        public_hits = await self._search_public_records(company_name)
        internal_hits = self._find_internal_signals(company_name)
        
        all_hits = public_hits + internal_hits

        if not all_hits:
            return self._empty_result(f"No AI leadership signals found for {company_name}")

        # Tiers are weighted by organizational impact, with strategic roles carrying the most weight
        tiers = set(h["tier"] for h in all_hits)
        base_score = 0
        if "STRATEGIC" in tiers: base_score = 60
        elif "OPERATIONAL" in tiers: base_score = 45
        elif "MANAGEMENT" in tiers: base_score = 30
        
        bonus = min(len(all_hits) * 8, 40)
        final_score = min(base_score + bonus, 100)

        return CollectorResult(
            category=SignalCategory.LEADERSHIP_SIGNALS,
            normalized_score=round(float(final_score), 2),
            confidence=0.85,
            raw_value=f"Identified {len(all_hits)} specialized leadership markers",
            source="News & Internal Data",
            metadata={
                "leadership_evidence": all_hits,
                "seniority_tiers": list(tiers),
                "signals_count": len(all_hits)
            }
        )

    def _empty_result(self, msg: str) -> CollectorResult:
        return CollectorResult(
            category=SignalCategory.LEADERSHIP_SIGNALS,
            normalized_score=0,
            confidence=0.5,
            raw_value=msg,
            source="Search"
        )
