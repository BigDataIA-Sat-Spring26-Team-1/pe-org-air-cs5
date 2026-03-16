import asyncio
import random
import time
import logging
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StealthLinkedInScraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        self.stealth_config = Stealth()

    async def get_description(self, url: str) -> str:
        """Scrapes the job description from a LinkedIn URL using Playwright Stealth."""
        if not url or "linkedin.com" not in url:
            return ""

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            
            # Create context with a random User Agent
            context = await browser.new_context(
                user_agent=random.choice(self.user_agents),
                viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)}
            )

            page = await context.new_page()
            
            # Apply stealth
            await self.stealth_config.apply_stealth_async(page)
            
            try:
                logging.info(f"Stealth scraping: {url}")
                
                # Add some jitter before navigation
                await asyncio.sleep(random.uniform(2, 5))
                
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Randomized scroll to mimic human behavior
                await page.mouse.wheel(0, random.randint(400, 800))
                await asyncio.sleep(random.uniform(3, 6))

                # Look for description selectors
                description_selectors = [
                    ".description__text", 
                    ".show-more-less-html__markup",
                    "section.description",
                    ".jobs-description__container",
                    ".main-card",
                    "article"
                ]
                
                description_text = ""
                for selector in description_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000)
                        if element:
                            description_text = await element.inner_text()
                            if len(description_text) > 100:
                                break
                    except:
                        continue
                
                if not description_text or len(description_text) < 100:
                    logging.warning("Standard selectors failed, extracting all text...")
                    description_text = await page.evaluate("() => document.body.innerText")
                    if "Job Description" in description_text:
                        description_text = description_text.split("Job Description")[-1]

                await browser.close()
                return description_text.strip()

            except Exception as e:
                logging.error(f"Playwright scraping failed: {e}")
                await browser.close()
                return ""

def run_stealth_scrape(url: str):
    """Sync wrapper for the async scraper."""
    scraper = StealthLinkedInScraper()
    return asyncio.run(scraper.get_description(url))

if __name__ == "__main__":
    test_url = "https://www.linkedin.com/jobs/view/4368378286"
    result = run_stealth_scrape(test_url)
    if result:
        print(f"Scraped Description (first 500 chars):\n{result[:500]}...")
    else:
        print("Failed to scrape description.")
