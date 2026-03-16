import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple

import aiohttp
import pandas as pd

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Patent:
    patent_number: str
    title: str
    abstract: str
    filing_date: Optional[datetime]
    cpc: List[str] = field(default_factory=list)
    ipc: List[str] = field(default_factory=list)
    is_ai_related: bool = False
    ai_categories: List[str] = field(default_factory=list)


# -----------------------------
# Rate limiter (<= 45 req/min)
# -----------------------------
class AsyncRateLimiter:
    """
    Simple spacing limiter: ensures at least `min_interval` seconds between requests.
    Also supports server-driven backoff via Retry-After on 429.
    """
    def __init__(self, requests_per_minute: int = 45):
        self.min_interval = 60.0 / float(requests_per_minute)
        self._lock = asyncio.Lock()
        self._last_ts = 0.0

    async def wait_turn(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_ts
            sleep_for = self.min_interval - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            self._last_ts = asyncio.get_event_loop().time()


# -----------------------------
# PatentsView client
# -----------------------------
class PatentsViewClient:
    """
    PatentsView PatentSearch API client.
    Docs: Search API requires X-Api-Key and has 45 req/min limit.
    """
    BASE = "https://search.patentsview.org/api/v1"

    def __init__(self, api_key: str, rpm: int = 45, timeout_sec: int = 60):
        self.api_key = api_key
        self.limiter = AsyncRateLimiter(requests_per_minute=rpm)
        self.timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async def _request_json(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        q: Dict[str, Any],
        f: List[str],
        s: Optional[List[Dict[str, str]]] = None,
        o: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        max_retries: int = 6,
    ) -> Dict[str, Any]:
        url = f"{self.BASE}{endpoint}"

        payload: Dict[str, Any] = {"q": q, "f": f}
        if s is not None:
            payload["s"] = s
        if o is not None:
            payload["o"] = o

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for attempt in range(max_retries):
            await self.limiter.wait_turn()

            try:
                async with session.request(method, url, json=payload, headers=headers) as resp:
                    # Handle throttling
                    if resp.status == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait_s = int(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt)
                        logging.warning(f"429 Too Many Requests. Retry-After={retry_after}. Sleeping {wait_s}s...")
                        await asyncio.sleep(wait_s)
                        continue

                    if resp.status in (500, 502, 503, 504):
                        wait_s = 2 ** attempt
                        logging.warning(f"{resp.status} server error. Sleeping {wait_s}s then retry...")
                        await asyncio.sleep(wait_s)
                        continue

                    if resp.status == 403:
                        text = await resp.text()
                        raise RuntimeError(
                            "403 Forbidden from PatentsView. Check X-Api-Key and that you're using the Search API domain.\n"
                            f"Response: {text[:500]}"
                        )

                    resp.raise_for_status()
                    return await resp.json()

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                wait_s = 2 ** attempt
                logging.warning(f"Request error: {e}. Sleeping {wait_s}s then retry...")
                await asyncio.sleep(wait_s)

        raise RuntimeError(f"Failed after {max_retries} retries: {endpoint}")

    async def iter_patents_by_assignee(
        self,
        company_variants: List[str],
        earliest_app_date_gte: str,
        page_size: int = 1000,
        max_pages: Optional[int] = None,
    ):
        """
        Uses cursor-like pagination with `o.after` and sort by patent_id asc.
        """
        # Query: (assignee org matches any variant) AND (earliest app date >= cutoff)
        assignee_or = [{"_text_phrase": {"assignees.assignee_organization": v}} for v in company_variants]
        q = {
            "_and": [
                {"_gte": {"patent_earliest_application_date": earliest_app_date_gte}},
                {"_or": assignee_or},
            ]
        }

        # Fields: include CPC + IPC + core metadata
        f = [
            "patent_id",
            "patent_title",
            "patent_abstract",
            "patent_earliest_application_date",
            "assignees.assignee_organization",
            "cpc_current.cpc_subclass_id",
            "cpc_current.cpc_group_id",
            "cpc_current.cpc_class_id",
            "ipcr.ipc_subclass",
            "ipcr.ipc_main_group",
            "ipcr.ipc_subgroup",
        ]

        s = [{"patent_id": "asc"}]
        after = None
        pages = 0

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            while True:
                o = {"size": page_size}
                if after is not None:
                    o["after"] = [after]

                data = await self._request_json(session, "/patent/", q=q, f=f, s=s, o=o, method="POST")
                patents = data.get("patents", [])
                total_hits = data.get("total_hits", 0)

                if not patents:
                    break

                yield patents, total_hits

                pages += 1
                if max_pages is not None and pages >= max_pages:
                    break

                # Next cursor: last patent_id (since sorted asc by patent_id)
                after = patents[-1].get("patent_id")
                if after is None:
                    break


# -----------------------------
# Collector (AI logic + output)
# -----------------------------
class PatentSignalCollectorPatentsView:
    # Your keyword list (kept) + a couple common shorthands
    AI_PATENT_KEYWORDS = [
        "machine learning", "neural network", "deep learning",
        "artificial intelligence", "natural language processing",
        "computer vision", "reinforcement learning", "pattern recognition",
        "information retrieval", "statistical learning", "autonomous",
        "predictive modeling", "classification algorithm", "heuristic",
        "optimization algorithm", "probabilistic model", "generative model",
        "transformer network", "semantic analysis", "image analysis",
        "signal processing", "backpropagation",
        # useful shorthands
        "ml", "ai", "llm", "transformer", "embedding"
    ]

    # CPC/IPC prefixes that align with your keyword themes (see notes + citations in chat)
    AI_CPC_PREFIXES = [
        "G06N",      # ML/AI computational models
        "G06F40",    # NLP / semantic
        "G06F16",    # information retrieval
        "G06T",      # image processing
        "G06V",      # image/video recognition
        "G10L",      # speech recognition/processing
    ]
    AI_IPC_PREFIXES = [
        "G06N",      # IPC also includes ML groups
        "G06F40",
        "G06F16",
        "G06T",
        "G06V",
        "G10L",
    ]

    def __init__(self, output_file: str = "patent_signals.csv"):
        self.output_file = output_file
        api_key = os.getenv("PATENTSVIEW_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "Missing PATENTSVIEW_API_KEY env var. "
                "Set it: export PATENTSVIEW_API_KEY='...'"
            )
        self.client = PatentsViewClient(api_key=api_key, rpm=45)

    @staticmethod
    def normalize_company_variants(company_name: str) -> List[str]:
        """
        Create a small set of safe variants without going wild (keeps queries efficient).
        """
        base = company_name.strip()
        # remove common suffixes
        cleaned = re.sub(r"\b(inc|inc\.|corp|corp\.|corporation|ltd|ltd\.|llc|plc|co|co\.)\b", "", base, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        variants = list(dict.fromkeys([base, cleaned]))  # preserve order, unique
        # If base has commas/periods, add a punctuation-light version
        punct_light = re.sub(r"[,\.\(\)]", "", base).strip()
        if punct_light and punct_light not in variants:
            variants.append(punct_light)

        # keep only non-empty
        return [v for v in variants if v]

    def extract_cpc_symbols(self, patent_row: Dict[str, Any]) -> List[str]:
        cpcs = []
        for item in patent_row.get("cpc_current", []) or []:
            # prefer group_id (most specific), else subclass_id/class_id
            for key in ("cpc_group_id", "cpc_subclass_id", "cpc_class_id"):
                val = item.get(key)
                if val:
                    cpcs.append(val.replace(" ", ""))
        return sorted(set(cpcs))

    def extract_ipc_symbols(self, patent_row: Dict[str, Any]) -> List[str]:
        ipcs = []
        for item in patent_row.get("ipcr", []) or []:
            sub = (item.get("ipc_subclass") or "").replace(" ", "")
            main = (item.get("ipc_main_group") or "").replace(" ", "")
            subg = (item.get("ipc_subgroup") or "").replace(" ", "")
            # construct a readable-ish symbol; not perfect but good for prefix matching
            symbol = f"{sub}{main}{subg}"
            symbol = symbol.strip()
            if symbol:
                ipcs.append(symbol)
        return sorted(set(ipcs))

    def classify_patent(self, patent: Patent) -> Patent:
        text = f"{patent.title} {patent.abstract}".lower()

        # Keyword match
        kw_hit = any(kw in text for kw in self.AI_PATENT_KEYWORDS)

        # Classification match (prefix)
        cpc_hit = any(any(cpc.startswith(pref) for pref in self.AI_CPC_PREFIXES) for cpc in patent.cpc)
        ipc_hit = any(any(ipc.startswith(pref) for pref in self.AI_IPC_PREFIXES) for ipc in patent.ipc)

        categories = []
        if any(k in text for k in ["neural", "deep learning", "transformer", "backpropagation", "autoencoder", "gan"]):
            categories.append("deep_learning")
        if any(k in text for k in ["vision", "image", "object detection", "pattern recognition", "signal processing"]):
            categories.append("computer_vision")
        if any(k in text for k in ["predictive", "forecasting", "probabilistic", "statistical learning", "classification"]):
            categories.append("predictive_analytics")
        if any(k in text for k in ["natural language", "nlp", "semantic", "text mining", "information retrieval"]):
            categories.append("nlp")
        if any(k in text for k in ["generative", "gpt", "llm", "large language model", "diffusion model"]):
            categories.append("generative_ai")

        patent.is_ai_related = kw_hit or cpc_hit or ipc_hit or (len(categories) > 0)
        patent.ai_categories = sorted(set(categories))

        return patent

    def analyze_patents(self, company_name: str, patents: List[Patent]) -> Dict[str, Any]:
        """
        Your 5/2/10 scoring, same as before.
        """
        now = datetime.now()
        last_year_cutoff = now - timedelta(days=365)

        ai_patents = [p for p in patents if p.is_ai_related]
        recent_ai = [p for p in ai_patents if p.filing_date and p.filing_date > last_year_cutoff]

        categories: Set[str] = set()
        for p in ai_patents:
            categories.update(p.ai_categories)

        patent_count_score = min(len(ai_patents) * 5, 50)
        recency_bonus = min(len(recent_ai) * 2, 20)
        category_score = min(len(categories) * 10, 30)

        score = patent_count_score + recency_bonus + category_score

        return {
            "company_name": company_name,
            "category": "INNOVATION_ACTIVITY",
            "source": "PATENTSVIEW_USPTO",
            "signal_date": datetime.now(timezone.utc).isoformat(),
            "raw_value": f"{len(ai_patents)} AI patents identified",
            "normalized_score": round(score, 1),
            "confidence": 0.9,
            "total_ai_patents": len(ai_patents),
            "recent_ai_patents": len(recent_ai),
            "categories": ",".join(sorted(categories)),
        }

    async def fetch_patents(self, company_name: str, years: int = 5) -> List[Patent]:
        variants = self.normalize_company_variants(company_name)
        cutoff = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

        logging.info(f"PatentsView: fetching patents for assignee variants={variants}, cutoff={cutoff}")

        out: List[Patent] = []
        seen_ids: Set[str] = set()

        async for patent_rows, total_hits in self.client.iter_patents_by_assignee(
            company_variants=variants,
            earliest_app_date_gte=cutoff,
            page_size=1000,
            max_pages=None,
        ):
            logging.info(f"Fetched page: {len(patent_rows)} records (total_hits={total_hits})")

            for row in patent_rows:
                pid = str(row.get("patent_id") or "").strip()
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)

                title = row.get("patent_title") or ""
                abstract = row.get("patent_abstract") or ""

                # filing date (earliest application date)
                filing_date = None
                dt = row.get("patent_earliest_application_date")
                if dt:
                    try:
                        filing_date = datetime.strptime(dt, "%Y-%m-%d")
                    except Exception:
                        filing_date = None

                patent = Patent(
                    patent_number=pid,
                    title=title,
                    abstract=abstract,
                    filing_date=filing_date,
                    cpc=self.extract_cpc_symbols(row),
                    ipc=self.extract_ipc_symbols(row),
                )
                out.append(self.classify_patent(patent))

        return out

    async def run(self, company_name: str, years: int = 5) -> Dict[str, Any]:
        patents = await self.fetch_patents(company_name, years)
        signal = self.analyze_patents(company_name, patents)

        logging.info(f"Signal for {company_name}: {signal}")

        # Save summary
        df_signal = pd.DataFrame([signal])
        if os.path.exists(self.output_file):
            pd.concat([pd.read_csv(self.output_file), df_signal], ignore_index=True).to_csv(self.output_file, index=False)
        else:
            df_signal.to_csv(self.output_file, index=False)

        # Save detailed
        detailed_file = "detailed_patents.csv"
        rows = []
        for p in patents:
            rows.append({
                "company": company_name,
                "patent_number": p.patent_number,
                "title": p.title,
                "url": f"https://patents.google.com/patent/US{p.patent_number}",  # just a convenient viewer link
                "is_ai_related": p.is_ai_related,
                "ai_categories": ",".join(p.ai_categories),
                "filing_date": p.filing_date.strftime("%Y-%m-%d") if p.filing_date else "",
                "cpc": ",".join(p.cpc),
                "ipc": ",".join(p.ipc),
                "abstract_snippet": (p.abstract[:500] if p.abstract else ""),
            })

        if rows:
            df = pd.DataFrame(rows)
            if os.path.exists(detailed_file):
                history = pd.read_csv(detailed_file)
                df = df[~df["patent_number"].isin(history["patent_number"].astype(str))]
                if not df.empty:
                    pd.concat([history, df], ignore_index=True).to_csv(detailed_file, index=False)
            else:
                df.to_csv(detailed_file, index=False)

            logging.info(f"Saved {len(rows)} patent rows to {detailed_file}")

        return signal


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--years", type=int, default=5)
    args = parser.parse_args()

    collector = PatentSignalCollectorPatentsView()
    asyncio.run(collector.run(args.company, args.years))