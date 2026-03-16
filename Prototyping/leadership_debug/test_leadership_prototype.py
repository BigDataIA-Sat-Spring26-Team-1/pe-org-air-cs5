import asyncio
import logging
import re
import os
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
from difflib import SequenceMatcher
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Leadership-Prototype")

# --- Standing on the exact logic from LeadershipCollector ---

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

LEADERSHIP_CONTEXT_KEYWORDS = [
    r"reports to the (?:chief ai officer|caio|vp of ai|head of ai)",
    r"reporting to (?:chief ai officer|caio|vp of ai|head of ai)",
    r"reports to (?:cto|chief technology officer) on ai strategy",
    r"collaborates with the (?:caio|chief ai officer)",
    r"leadership team",
    r"strategic ai initiative"
]

# --- Replicating WebUtils.get_page_items functionality here to be standalone ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

async def standalone_get_search_results(query: str):
    """Standalone search fetcher that mimics the platform's behavior."""
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # We skip stealth for this prototype to observe if blocks happen
        context = await browser.new_context(user_agent=USER_AGENTS[0])
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            # Fetch all h3 titles and their surrounding text (mimicking the platform's selector)
            items = await page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('h3').forEach(el => {
                    const title = el.innerText;
                    const container = el.closest('div.g') || el.parentElement?.parentElement;
                    const snippet = container ? container.innerText : "";
                    if (title.length > 5) {
                        results.push({ title, snippet });
                    }
                });
                
                // CRITICAL: The platform has a fallback to body text if no structured results found
                if (results.length === 0) {
                    const bodyText = document.body.innerText;
                    // BLOCKER: Detect Google's specific block text
                    const blockedStrings = [
                        "reCAPTCHA", "automated requests", "unusual traffic", 
                        "really you sending the requests", "not a robot"
                    ];
                    if (blockedStrings.some(s => bodyText.includes(s)) || bodyText.includes("did not match any documents")) {
                        return [];
                    }
                    results.push({ 
                        title: "Raw results (Fallback)", 
                        snippet: bodyText 
                    });
                }
                return results;
            }""")
            return items
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        finally:
            await browser.close()

# --- The Prototype Class ---

class LeadershipPrototype:
    def __init__(self, jobs_file: str = "processed_jobs.csv"):
        self.jobs_file = jobs_file

    def _analyze_job_descriptions(self, company_name: str, ticker: str) -> List[Dict[str, str]]:
        """Scans job descriptions for leadership context or reporting lines."""
        results = []
        if not os.path.exists(self.jobs_file):
            logger.info("No local jobs file found for deep analysis.")
            return results

        try:
            df = pd.read_csv(self.jobs_file)
            # Use the robust matcher we defined in tech/hiring (simplified for prototype)
            t_name = company_name.lower()
            
            for _, row in df.iterrows():
                listing_comp = str(row.get('company', '')).lower()
                if ticker.lower() not in listing_comp and t_name[:5] not in listing_comp:
                    continue
                
                title = str(row.get('title', '')).lower()
                desc = str(row.get('description', '')).lower()
                context = f"{title} {desc}"
                
                # Check for direct leadership roles (The old way)
                for role in TARGET_ROLES:
                    if re.search(r'\b' + re.escape(role) + r'\b', title):
                        results.append({
                            "role": role.upper(),
                            "tier": _assess_rank(role),
                            "source": "Job Title",
                            "context": title
                        })
                        break
                
                # NEW: Check for reporting context or mentions of AI leadership (The "Reporting To" way)
                for pattern in LEADERSHIP_CONTEXT_KEYWORDS:
                    if re.search(pattern, desc):
                        results.append({
                            "role": "MENTIONED LEADERSHIP",
                            "tier": "OPERATIONAL", # Usually operational if reporting to CAIO
                            "source": "Reporting Context",
                            "context": f"Matched pattern: {pattern} in {title}"
                        })
                        break
        except Exception as e:
            logger.error(f"Job leadership analysis failed: {e}")
            
        return results

    async def collect(self, company_name: str, ticker: str):
        logger.info(f"Checking leadership for {company_name}")
        
        # 1. Replicating the exact search query construction
        clean_name = company_name.replace("Inc.", "").replace("Corp.", "").strip()
        queries = [
            f'"{clean_name}" (appointed OR joined OR named) ({ "|".join(TARGET_ROLES[:5]) })',
            f'{clean_name} "Head of AI" news',
            f'{clean_name} "Chief AI Officer" 2024..2025'
        ]
        
        all_detections = []
        for q in queries:
            logger.info(f"Querying: {q}")
            items = await standalone_get_search_results(q)
            
            for item in items:
                combined_text = f"{item['title']} {item['snippet']}".lower()
                
                if item['title'] == "Raw results (Fallback)":
                    logger.info(f" --- FALLBACK DETECTED --- ")
                    logger.info(f" BODY SNIPPET: {combined_text[:500]}...")

                # STRICT REGEX FIX
                for role in TARGET_ROLES:
                    # FIX: Use word boundaries to stop matching 'caio' in 'q=caio' from search URLs
                    if re.search(r'\b' + re.escape(role) + r'\b', combined_text, re.IGNORECASE):
                        det = {
                            "role": role.upper(),
                            "tier": _assess_rank(role),
                            "context": item['title'],
                            "source": "Search Result"
                        }
                        all_detections.append(det)
                        logger.info(f" [+] FOUND (Search): {role.upper()} ({det['tier']})")
                        break
        
        # 2. Internal deep scan of jobs (Reporting lines/context)
        internal_hits = self._analyze_job_descriptions(company_name, ticker)
        for hit in internal_hits:
            logger.info(f" [+] FOUND (Jobs): {hit['role']} via {hit['source']}")
        
        all_hits = all_detections + internal_hits
        
        # 3. Scoring (Exact replication)
        if not all_hits:
            logger.error("No signals found.")
            return 0
            
        tiers = set(h["tier"] for h in all_hits)
        base_score = 0
        if "STRATEGIC" in tiers: base_score = 60
        elif "OPERATIONAL" in tiers: base_score = 45
        elif "MANAGEMENT" in tiers: base_score = 30
        
        bonus = min(len(all_detections) * 8, 40)
        final_score = min(base_score + bonus, 100)
        
        logger.info(f"FINAL SCORE: {final_score} (Detections: {len(all_detections)})")
        return final_score

async def run_debug():
    from app.pipelines.external_signals.job_collector import JobCollector
    
    # 1. RUN JOB PIPELINE FIRST
    companies = [
        ("JPMorgan Chase", "JPM"),
        ("Goldman Sachs", "GS"),
        ("Walmart", "WMT")
    ]
    
    # We use a shared jobs file for the prototype
    jobs_file = "leadership_test_jobs.csv"
    job_collector = JobCollector(output_file=jobs_file)
    
    logger.info("=== STEP 1: RUNNING JOB PIPELINE ===")
    for name, ticker in companies:
        logger.info(f"--- Scraping jobs for {name} ---")
        # We use JobCollector which now has our Alphanumeric + Similarity fixes
        await job_collector.collect(name, ticker=ticker, days=14)
        # Avoid rate limits
        await asyncio.sleep(3)

    # 2. RUN LEADERSHIP PIPELINE
    logger.info("\n=== STEP 2: RUNNING LEADERSHIP PIPELINE ===")
    proto = LeadershipPrototype(jobs_file=jobs_file)
    
    for name, ticker in companies:
        score = await proto.collect(name, ticker)
        logger.info(f"FINAL RESULT for {name}: {score}")
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_debug())
