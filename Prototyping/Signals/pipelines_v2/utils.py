import asyncio
import random
import logging
import re
from typing import Optional, List, Dict
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Configure module-level logger
logger = logging.getLogger(__name__)

class WebUtils:
    """Helper class for web operations and text cleaning."""
    
    # Common User-Agents to rotate and avoid basic bot detection
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]

    @staticmethod
    def clean_company_name(name: str) -> str:
        """Removes corporate legal suffixes to improve search results."""
        suffixes = [
            r"\bInc\.?\b", r"\bCorp(oration)?\.?\b", r"\bLLC\b", 
            r"\bLtd\.?\b", r"\bGroup\b", r"\bPLC\b", r"\bS\.A\.?\b"
        ]
        clean_name = name
        for suffix in suffixes:
            clean_name = re.sub(suffix, "", clean_name, flags=re.IGNORECASE)
        
        # Remove any dangling spaces, commas, or periods
        clean_name = clean_name.strip()
        clean_name = re.sub(r'[^a-zA-Z0-9]+$', '', clean_name)
        return clean_name.strip()

    @staticmethod
    async def get_page_items(url: str, selector: str = "h3") -> List[Dict[str, str]]:
        """Fetches structured items from a page, specifically tuned for search engines."""
        if not url:
            return []
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-http2', '--no-sandbox']
            )
            context = await browser.new_context(
                user_agent=random.choice(WebUtils.USER_AGENTS),
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()
            
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Google specific wait
                if "google.com" in url:
                    try: await page.wait_for_selector(selector, timeout=10000)
                    except: pass

                items = await page.evaluate(f"""(sel) => {{
                    const results = [];
                    document.querySelectorAll(sel).forEach(el => {{
                        const title = el.innerText;
                        const container = el.closest('div.g') || el.parentElement?.parentElement;
                        const snippet = container ? container.innerText : "";
                        if (title.length > 5) {{
                            results.push({{ title, snippet }});
                        }}
                    }});
                    
                    // Fallback to body text if no structured results found
                    if (results.length === 0) {{
                        results.push({{ 
                            title: "Raw results (Fallback)", 
                            snippet: document.body.innerText 
                        }});
                    }}
                    return results;
                }}""", selector)
                
                return items
            except Exception as e:
                logger.error(f"Search fetch failed for {url}: {e}")
                return []
            finally:
                await browser.close()

    @staticmethod
    async def fetch_page_text(url: str) -> str:
        """Directly visits a URL and extracts readable text with a fallback mechanism."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=['--disable-http2'])
            context = await browser.new_context(user_agent=random.choice(WebUtils.USER_AGENTS))
            page = await context.new_page()
            
            # Apply stealth to avoid bot detection on direct visits
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            try:
                # We use a slightly more patient wait strategy
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # BuiltWith specific wait for dynamic content
                if "builtwith.com" in url:
                    try: await page.wait_for_load_state("networkidle", timeout=10000)
                    except: pass
                else:
                    await asyncio.sleep(2) # Give dynamic content time to render
                
                # First attempt: Get readable text from the body
                try:
                    content = await page.inner_text("body", timeout=5000)
                except:
                    # Fallback: Get full page source if inner_text fails
                    content = await page.content()
                
                return content.strip().lower()
            except Exception as e:
                logger.debug(f"Direct visit to {url} failed: {e}")
                # Fallback to search-style results if it was a search URL
                return ""
            finally:
                await browser.close()

    @staticmethod
    async def get_page_content(url: str) -> str:
        """Utility for general text retrieval from search or direct URL."""
        if "google.com" in url or "search" in url:
            items = await WebUtils.get_page_items(url)
            return " ".join([f"{i['title']} {i['snippet']}" for i in items])
        else:
            return await WebUtils.fetch_page_text(url)
