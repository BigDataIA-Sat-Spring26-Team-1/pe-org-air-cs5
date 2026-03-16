import asyncio
import os
import pandas as pd
import logging
import random
import re
from typing import List, Dict, Any
from datetime import datetime
from .utils import WebUtils
from app.models.signals import CollectorResult, SignalCategory, SignalEvidenceItem

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


    async def collect(self, company_name: str, ticker: str = None) -> CollectorResult:
        """Identifies leadership indicators using news, board data, and internal markers."""
        logger.info(f"Scanning leadership structure for {company_name}")
        
        from app.services.snowflake import db
        all_hits = []
        try:
            # 1. Search public records (News/Press Releases)
            public_hits = await self._search_public_records(company_name)
            all_hits.extend(public_hits)
            
            # 2. Look for internal leadership in Snowflake (Jobs)
            company_rec = await db.fetch_company_by_ticker(ticker) if ticker else None
            if company_rec:
                job_descs = await db.fetch_all(
                    "SELECT title, description FROM signal_evidence WHERE company_id = %s AND category = 'technology_hiring'", 
                    (company_rec['id'],)
                )
                for job in job_descs:
                    title = job.get('title', '').lower()
                    if any(role in title for role in self.TARGET_ROLES):
                        all_hits.append({
                            "role": title.upper(),
                            "tier": self._assess_rank(title),
                            "context": "Senior AI role detected in recruitment signals.",
                            "source": "Internal Recruitment"
                        })

        except Exception as e:
            logger.error(f"Leadership collection failed: {e}", exc_info=True)
            # Proceed with whatever hits we found before the crash
        
        if not all_hits:
            return self._empty_result(f"No AI leadership signals found for {company_name}")

        # Tiers are weighted by organizational impact
        tiers = set(h["tier"] for h in all_hits)
        base_score = 0
        if "STRATEGIC" in tiers: base_score = 65 # Slightly higher due to board signals
        elif "OPERATIONAL" in tiers: base_score = 50
        elif "MANAGEMENT" in tiers: base_score = 35
        
        # Deduplicate hits by role and source to avoid scoring twice
        unique_hits = []
        seen = set()
        for h in all_hits:
            key = f"{h['role']}_{h['source']}"
            if key not in seen:
                unique_hits.append(h)
                seen.add(key)

        bonus = min(len(unique_hits) * 7, 35)
        final_score = min(base_score + bonus, 100)

        evidence_items = [
            SignalEvidenceItem(
                title=f"{h['tier']} Role: {h.get('role', 'Executive Focus')}",
                description=h.get('context', 'Strategic AI Alignment Signal'),
                tags=[h['tier'], "Leadership", "Organization"],
                date=datetime.now().date().isoformat(),
                metadata={"role": h.get('role'), "impact": h.get('tier'), "source_type": h.get('source')}
            )
            for h in unique_hits
        ]

        return CollectorResult(
            category=SignalCategory.LEADERSHIP_SIGNALS,
            normalized_score=round(float(final_score), 2),
            confidence=0.85,
            raw_value=f"Identified {len(all_hits)} specialized leadership markers",
            source="Internal Signals Analysis",
            evidence=evidence_items,
            metadata={
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
