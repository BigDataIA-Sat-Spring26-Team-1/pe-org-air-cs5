import asyncio
import logging
import re
from typing import List, Dict, Any
from datetime import datetime
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Leadership-Verify")

# --- Logic from app/pipelines/external_signals/leadership_collector.py ---

TARGET_ROLES = [
    "chief ai officer", "caio", "chief artificial intelligence officer",
    "vp of ai", "vice president of artificial intelligence",
    "director of ai", "head of ai", "director of machine learning",
    "head of data science", "chief data scientist", "chief ai scientist",
    "chief data and ai officer", "caido", "vp of generative ai",
    "vp of machine learning", "vp of ai transformation", "head of autonomy"
]

def _assess_rank(title: str) -> str:
    t = title.lower()
    if any(x in t for x in ["chief", "president", "caio", "caido"]): return "STRATEGIC"
    if any(x in t for x in ["vp", "vice president", "evp", "svp", "managing director"]): return "OPERATIONAL"
    if any(x in t for x in ["director", "head", "gm", "general manager"]): return "MANAGEMENT"
    return "SPECIALIST"

async def verify_leadership(company_name: str, ticker: str):
    logger.info(f"\n--- VERIFYING LEADERSHIP FOR {company_name} ---")
    
    # Use the real WebUtils to see what we get
    from app.pipelines.external_signals.utils import WebUtils
    
    clean_name = WebUtils.clean_company_name(company_name)
    queries = [
        f'"{clean_name}" "Chief AI Officer"',
        f'"{clean_name}" "Head of AI"',
        f'"{clean_name}" "VP of AI"'
    ]
    
    all_hits = []
    for q in queries:
        url = f"https://www.google.com/search?q={q.replace(' ', '+')}"
        logger.info(f"Searching: {url}")
        items = await WebUtils.get_page_items(url)
        
        logger.info(f"Received {len(items)} items from search.")
        for item in items:
            title = item.get('title', '')
            snippet = item.get('snippet', '')
            combined = f"{title} {snippet}".lower()
            
            # Check for fallback marker
            if title == "Raw results (Fallback)":
                logger.warning(f"  [!] RECOGNIZED FALLBACK TEXT (Search Blocked?)")
                # Show a bit of the snippet to see if it contains roles
                logger.info(f"  Snippet start: {snippet[:200]}...")
            
            for role in TARGET_ROLES:
                # Use word boundaries for better matching
                if re.search(r'\b' + re.escape(role) + r'\b', combined, re.IGNORECASE):
                    hit = {
                        "role": role.upper(),
                        "tier": _assess_rank(role),
                        "context": title
                    }
                    all_hits.append(hit)
                    logger.info(f"  [+] Match: {role.upper()} ({hit['tier']}) in '{title}'")
                    break 

    # Calculation
    if not all_hits:
        logger.error("No leadership signals found.")
    else:
        tiers = set(h["tier"] for h in all_hits)
        base = 0
        if "STRATEGIC" in tiers: base = 60
        elif "OPERATIONAL" in tiers: base = 45
        elif "MANAGEMENT" in tiers: base = 30
        
        bonus = min(len(all_hits) * 8, 40)
        final = min(base + bonus, 100)
        logger.info(f"Final Simulated Score: {final}")

if __name__ == "__main__":
    companies = [
        ("JPMorgan Chase", "JPM"),
        ("Goldman Sachs", "GS"),
        ("Walmart", "WMT")
    ]
    
    async def run_all():
        for name, ticker in companies:
            await verify_leadership(name, ticker)
            await asyncio.sleep(2) # Avoid aggressive searching
            
    asyncio.run(run_all())
