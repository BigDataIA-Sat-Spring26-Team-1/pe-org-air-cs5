import asyncio
import logging
import re
from typing import List, Dict, Any
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Leadership-Debug")

# --- Logic copied from app/pipelines/external_signals/leadership_collector.py ---

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

# Mock WebUtils for testing
class MockWebUtils:
    @staticmethod
    def clean_company_name(name: str) -> str:
        return name.replace("Inc.", "").replace("Corp.", "").strip()

    @staticmethod
    async def get_page_items(url: str):
        # This will be replaced by real calls in the test
        return []

async def debug_leadership(company_name: str, ticker: str):
    logger.info(f"\n--- DEBUGGING LEADERSHIP FOR {company_name} ({ticker}) ---")
    
    clean_name = MockWebUtils.clean_company_name(company_name)
    queries = [
        f'"{clean_name}" (appointed OR joined OR named) ({ "|".join(TARGET_ROLES[:5]) })',
        f'{clean_name} "Head of AI" news',
        f'{clean_name} "Chief AI Officer" 2024..2025'
    ]
    
    # We'll use a real tool to get search results if possible, 
    # but since I'm simulating, I'll just look at the regex issue.
    
    # PROBLEM HYPOTHESIS: "caio" or "vp" matching substrings.
    test_texts = [
        "Location: San Francisco, CA. I joined the team.", # Matches "ca" + "io"? No.
        "The company announced a new AI strategy.",
        "We are looking for a VP of AI.",
        "JPMorgan Chase named a new Chief AI Officer."
    ]
    
    detections = []
    # Simulating what actually happens in the collector
    # In reality, the collector finds something that results in score 68.
    
    # Let's see if we can find what's causing "STRATEGIC" to match so easily.
    # Note: "caio" is in TARGET_ROLES. 
    # If a snippet has "Location: CA, I..." -> "ca, i" -> "cai"
    # Actually, re.search("caio", "Location: CA, I joined") -> Matches "CA, I"? 
    # Let's check.
    
    sample_text = "Location: CA. I joined."
    if re.search("caio", sample_text.lower()):
        logger.info(f"MATCH FOUND for 'caio' in '{sample_text}'")
    
    # Another possibility: "CAIO" is a common Italian name or similar.
    
    # Let's try to run a real search for JPM and see the snippets.
    # I'll use the browser or search_web tool if available.
    # Wait, I have search_web!
    
    from app.pipelines.external_signals.utils import WebUtils

    for query in queries:
        logger.info(f"Searching for: {query}")
        # search_web is a tool, I can't call it directly from python unless I use the tool.
        # I'll just explain the logic and fix the regex.

if __name__ == "__main__":
    # I'll manually check the regex for "caio" and "vp"
    roles_to_check = ["caio", "caido", "vp"]
    texts_to_check = [
        "Location: CA. I office", # Matches "ca" + "i" + "o"? 
        "JPMorgan Chase & Co. (JPM)", # Matches "co."?
        "Education: ...",
    ]
    
    for r in roles_to_check:
        for t in texts_to_check:
            if re.search(r, t.lower()):
                print(f"Role '{r}' matched text '{t}'")
