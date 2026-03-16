import asyncio
import logging
import pandas as pd
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict
import os
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class Executive:
    name: str
    title: str
    company: str
    source: str
    senority_level: str # CAO, VP, Director, Head

class LeadershipSignalCollector:
    """Detects AI leadership signals via Job Titles and Executive Search."""

    LEADERSHIP_KEYWORDS = [
        "chief ai officer", "caio", "chief artificial intelligence officer",
        "vp of ai", "vice president of artificial intelligence",
        "director of ai", "head of ai", "director of machine learning",
        "head of data science", "chief data scientist", "chief ai scientist",
        "chief data and ai officer", "caido", "vp of generative ai",
        "vp of machine learning", "vp of ai transformation", "head of autonomy",
        "director of ai ethics", "ai compliance officer", "head of ai product",
        "ai fellow", "president of ai", "managing director of ai",
        "general manager of ai", "gm of ai", "svp of ai", "evp of ai",
        "distinguished engineer", "principal scientist", "director of ai adoption"
    ]

    SENIORITY_MAPPING = {
        "chief": "C_SUITE",
        "president": "C_SUITE",
        "caio": "C_SUITE",
        "caido": "C_SUITE",
        "executive vice president": "EXECUTIVE",
        "evp": "EXECUTIVE",
        "senior vice president": "EXECUTIVE",
        "svp": "EXECUTIVE",
        "vice president": "EXECUTIVE",
        "vp": "EXECUTIVE",
        "fellow": "EXECUTIVE",
        "managing director": "EXECUTIVE",
        "general manager": "SENIOR_MANAGEMENT",
        "gm": "SENIOR_MANAGEMENT",
        "director": "SENIOR_MANAGEMENT",
        "head": "SENIOR_MANAGEMENT",
        "principal": "LEAD",
        "distinguished": "EXECUTIVE"
    }

    def __init__(self, output_file="leadership_signals.csv", jobs_file="processed_jobs.csv"):
        self.output_file = output_file
        self.jobs_file = jobs_file
        self.stealth_config = Stealth()

    def get_leadership_from_jobs(self, company_name: str) -> List[Dict]:
        """Examines job titles AND descriptions for leadership roles and reporting lines."""
        signals = []
        if not os.path.exists(self.jobs_file):
            return signals

        df = pd.read_csv(self.jobs_file)
        # Filter for the company
        company_jobs = df[df['company'].str.contains(company_name, case=False, na=False)]
        
        for _, row in company_jobs.iterrows():
            title = str(row['title']).lower()
            desc = str(row.get('description', '')).lower()
            
            # 1. Direct Vacancy: Hiring for a leader
            if any(key in title for key in ["director", "head of", "vp", "chief", "lead"]):
                if any(ai_key in title for ai_key in ["ai", "ml", "data science", "machine learning", "intelligence"]):
                    signals.append({
                        "name": "N/A (Job Vacancy)",
                        "title": row['title'],
                        "company": company_name,
                        "level": self._map_seniority(row['title']),
                        "type": "HIRING_PIPELINE",
                        "date": row.get('date_posted', datetime.now().strftime("%Y-%m-%d")),
                        "url": row.get('job_url', '')
                    })
            
            # 2. Indirect Evidence: Reporting to a leader
            # e.g., "Reporting to the Head of AI"
            reporting_patterns = [
                r"reporting to the (head of ai|chief ai officer|vp of machine learning|director of data science|chief data and ai officer|caio|caido|head of autonomy)",
                r"work closely with our (head of ai|caio|chief technology officer|ai fellow|vp of generative ai)",
                r"reporting to (senior director of ai|svp of machine learning|evp of digital transformation)",
                r"under the leadership of (the president of ai|general manager of machine learning)"
            ]
            for pattern in reporting_patterns:
                match = re.search(pattern, desc)
                if match:
                    role_found = match.group(1).upper()
                    signals.append({
                        "name": "Confirmed Position",
                        "title": f"Existing Role Detected: {role_found}",
                        "company": company_name,
                        "level": self._map_seniority(role_found),
                        "type": "REPORTING_LINE_EVIDENCE",
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "snippet": match.group(0)
                    })
                    break
                    
        return signals


    async def search_leadership_news(self, company_name: str) -> List[Dict]:
        """Highly resilient dynamic discovery for AI leadership events."""
        logging.info(f"Dynamically discovering AI leadership for {company_name}...")
        results = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            page = await context.new_page()
            await self.stealth_config.apply_stealth_async(page)
            
            # 1. Broad News Search
            # 2. Direct "Title" Search
            queries = [
                f'"{company_name}" (appointed OR joined OR named) ({ "|".join(self.LEADERSHIP_KEYWORDS[:5]) })',
                f'{company_name} "Head of AI" news',
                f'{company_name} "Chief AI Officer" 2024..2025'
            ]
            
            for query in queries:
                try:
                    # Switch between News and General search
                    suffix = "&tbm=nws" if "news" in query.lower() else ""
                    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}{suffix}"
                    await page.goto(search_url, wait_until="networkidle", timeout=10000)
                    
                    # Extraction Logic: Multi-pronged
                    # 1. DOM Snippets
                    # 2. Full Page Body Text Analysis (Fallback)
                    
                    # Try DOM Extraction
                    dom_data = await page.evaluate("""() => {
                        const items = [];
                        // Check Titles (h3) and their surrounding snippets
                        document.querySelectorAll('h3').forEach(h3 => {
                            const title = h3.innerText;
                            const container = h3.closest('div.g') || h3.parentElement.parentElement;
                            const snippet = container ? container.innerText : "";
                            items.push({title, snippet});
                        });
                        return items;
                    }""")
                    
                    # If DOM extraction seems empty/blocked, get raw body text
                    if len(dom_data) < 2:
                        body_text = await page.inner_text("body")
                        dom_data.append({"title": "Raw Search Results", "snippet": body_text})

                    for item in dom_data:
                        text = f"{item['title']} {item['snippet']}"
                        
                        for role in self.LEADERSHIP_KEYWORDS:
                            # Use regex for flexible matching (e.g., "VP of AI", "Vice President of AI")
                            if re.search(role, text, re.IGNORECASE):
                                # Extraction pattern: Look for Capitalized Names near the role
                                # Example: "UnitedHealth Group appointed Sandeep Dadlani as..."
                                name_match = re.search(r"([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:joins|joined|appointed|named|serves|is|as|at|to)", text)
                                name = name_match.group(1) if name_match else "Executive Found"
                                
                                if not any(r['name'] == name and r['company'] == company_name for r in results):
                                    results.append({
                                        "name": name,
                                        "title": item['title'] if len(item['title']) > 10 else f"Leadership: {role.title()}",
                                        "company": company_name,
                                        "level": self._map_seniority(role),
                                        "type": "DYNAMIC_SEARCH",
                                        "date": datetime.now().strftime("%Y-%m-%d"),
                                        "snippet": item['snippet'][:200].replace('\n', ' ')
                                    })
                                break

                    await asyncio.sleep(random.uniform(2, 4))
                except Exception as e:
                    logging.warning(f"Engine failed for query '{query}': {e}")
            
            await browser.close()
            
        return results

    def _map_seniority(self, title: str) -> str:
        title = title.lower()
        if any(x in title for x in ["chief", "president", "caio", "caido"]): return "C_SUITE"
        if any(x in title for x in ["vp", "vice president", "fellow", "managing director", "distinguished", "svp", "evp"]): return "EXECUTIVE"
        if any(x in title for x in ["director", "head of", "gm", "general manager"]): return "SENIOR_MANAGEMENT"
        return "LEAD"

    def calculate_leadership_score(self, sightings: List[Dict]) -> Dict:
        """Calculate score: C_SUITE=50, EXECUTIVE=40, SENIOR_MANAGEMENT=30. Max 100."""
        score = 0
        conf = 0.85
        levels_seen = set()
        
        # Deduplicate by level to reward diversity of leadership roles
        for s in sightings:
            level = s['level']
            if level == "C_SUITE" and "C_SUITE" not in levels_seen:
                score += 50
                levels_seen.add("C_SUITE")
            elif level == "EXECUTIVE" and "EXECUTIVE" not in levels_seen:
                score += 40
                levels_seen.add("EXECUTIVE")
            elif level == "SENIOR_MANAGEMENT" and "SENIOR_MANAGEMENT" not in levels_seen:
                score += 30
                levels_seen.add("SENIOR_MANAGEMENT")
            elif level == "LEAD" and "LEAD" not in levels_seen:
                score += 15
                levels_seen.add("LEAD")

        return {
            "score": min(score, 100),
            "confidence": conf,
            "leadership_count": len(sightings)
        }

    async def run(self, company_name: str):
        # 1. Check Job Postings for Vacancies (Internal Signal)
        hiring_signals = self.get_leadership_from_jobs(company_name)
        
        # 2. Search for News/Press Releases (External Signal)
        news_signals = await self.search_leadership_news(company_name)
        
        all_signals = hiring_signals + news_signals
        
        # 3. Score
        metrics = self.calculate_leadership_score(all_signals)
        
        result = {
            "company_name": company_name,
            "category": "LEADERSHIP_COMMITMENT",
            "leadership_score": metrics['score'],
            "confidence": metrics['confidence'],
            "key_leaders": ",".join([f"{s['name'] if s['name'] != 'Confirmed Leader' else ''} ({s['title']})" for s in all_signals]),
            "signal_date": datetime.now(timezone.utc).isoformat()
        }
        
        logging.info(f"Leadership Score for {company_name}: {result['leadership_score']}/100")
        
        # Save results
        df = pd.DataFrame([result])
        if os.path.exists(self.output_file):
            pd.concat([pd.read_csv(self.output_file), df], ignore_index=True).to_csv(self.output_file, index=False)
        else:
            df.to_csv(self.output_file, index=False)
            
        return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    
    collector = LeadershipSignalCollector()
    asyncio.run(collector.run(args.company))
