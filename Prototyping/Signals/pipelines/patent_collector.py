import logging
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from google.cloud import bigquery
from .models import CollectorResult

# Configure logger
logger = logging.getLogger(__name__)

class PatentCollector:
    """
    Analyzes corporate innovation using BigQuery's public patent datasets.
    """

    AI_KEYWORDS = [
        "machine learning", "neural network", "deep learning",
        "artificial intelligence", "natural language processing",
        "computer vision", "reinforcement learning", "pattern recognition",
        "autonomous", "predictive modeling", "generative model", "transformer network", 
        "llm", "gpt", "model training"
    ]

    # Mapping of CPC prefixes to technology domains (In sync with 5/2/10 scoring)
    TECH_DOMAINS = {
        "autonomy": ["G05D", "B60W", "G01S", "G05B"],
        "ai_ml": ["G06N", "G06K", "G06F18"],
        "computer_vision": ["G06T", "G06V", "G01B"],
        "electrification": ["H02J", "H01M", "B60L", "H01T"],
        "digital_iot": ["G06Q", "H04L", "H04W", "G07C"]
    }

    def __init__(self, project_id: Optional[str] = None):
        self.client = bigquery.Client(project=project_id)

    def _prepare_query(self, company: str, years: int) -> str:
        """Forms the SQL query to retrieve patent filings with robust name cleaning."""
        
        # Clean company name for BigQuery (remove common suffixes)
        clean_company = company.upper()
        suffixes = [
            " INC.", " INC", " CORP.", " CORP", " LTD.", " LTD", 
            " GROUP", " LLC", " PLC", " & COMPANY", " & CO", " CO.", " CO"
        ]
        for suffix in suffixes:
            if suffix in clean_company:
                clean_company = clean_company.split(suffix)[0].strip()
        
        # Final safety check
        if " & " in clean_company:
            clean_company = clean_company.split(" & ")[0].strip()
        
        # BigQuery integer date format (YYYYMMDD)
        date_limit = (datetime.now().year - years) * 10000 + 101

        return f"""
        SELECT 
            p.publication_number,
            ANY_VALUE(p.title_localized[SAFE_OFFSET(0)].text) as title,
            ANY_VALUE(p.filing_date) as filing_date,
            COUNT(DISTINCT cit.publication_number) as forward_citations,
            ARRAY_AGG(DISTINCT c.code IGNORE NULLS) as codes
        FROM `bigquery-public-data.patents.publications` AS p
        LEFT JOIN UNNEST(p.assignee_harmonized) AS a
        LEFT JOIN UNNEST(p.cpc) AS c
        LEFT JOIN UNNEST(p.citation) AS cit
        WHERE a.name LIKE '{clean_company}%'
          AND p.filing_date > {date_limit}
        GROUP BY p.publication_number
        """

    def _process_records(self, df: pd.DataFrame) -> CollectorResult:
        """Analyzes retrieved records using the 5/2/10 rule."""
        if df.empty:
            return CollectorResult(
                normalized_score=0.0,
                confidence=0.8,
                raw_value="No patents found",
                metadata={"total_filings": 0}
            )

        now = datetime.now()
        last_year_cutoff = int((now - timedelta(days=365)).strftime("%Y%m%d"))
        
        ai_total = 0
        recent_ai = 0
        citation_sum = 0
        domains_hit = set()
        evidence = []

        for _, row in df.iterrows():
            title_text = str(row.get('title', '')).lower()
            codes_raw = row.get('codes')
            cpc_codes = codes_raw if codes_raw is not None and not (hasattr(codes_raw, 'size') and codes_raw.size == 0) else []

            is_ai_relevant = False
            matched_domains = []
            
            # Text based check
            if any(kw in title_text for kw in self.AI_KEYWORDS):
                is_ai_relevant = True
            
            # CPC based check
            for domain, prefixes in self.TECH_DOMAINS.items():
                if any(any(str(code).startswith(p) for p in prefixes) for code in cpc_codes):
                    is_ai_relevant = True
                    matched_domains.append(domain)

            if is_ai_relevant:
                ai_total += 1
                cites = int(row.get('forward_citations', 0))
                citation_sum += cites
                domains_hit.update(matched_domains)
                
                if int(row.get('filing_date', 0)) > last_year_cutoff:
                    recent_ai += 1
                
                # Capture high-impact evidence
                if len(evidence) < 5:
                    evidence.append({
                        "id": row['publication_number'],
                        "title": row.get('title'),
                        "cites": cites
                    })
                elif cites > min([e.get('cites', 0) for e in evidence]):
                    evidence.append({
                        "id": row['publication_number'],
                        "title": row.get('title'),
                        "cites": cites
                    })
                    evidence = sorted(evidence, key=lambda x: x['cites'], reverse=True)[:5]

        # 5/2/10 Rule: volume (50) + recency (20) + diversity (30)
        patent_volume_score = min(ai_total * 5, 50)
        recency_bonus = min(recent_ai * 2, 20)
        diversity_score = min(len(domains_hit) * 10, 30)
        
        final_score = patent_volume_score + recency_bonus + diversity_score

        return CollectorResult(
            normalized_score=float(final_score),
            confidence=1.0, # Registry data is high confidence
            raw_value=f"Identified {ai_total} AI patents from {len(df)} total filings",
            metadata={
                "total_filings": len(df),
                "ai_count": ai_total,
                "recent_filings": recent_ai,
                "domains": list(domains_hit),
                "citations": citation_sum,
                "high_impact": evidence
            }
        )

    def collect(self, company: str, years: int = 5) -> CollectorResult:
        """Orchestrates the patent collection and analysis process."""
        logger.info(f"Retrieving patent history for {company}")
        sql = self._prepare_query(company, years)
        
        try:
            results_df = self.client.query(sql).to_dataframe()
            logger.info(f"Retrieved {len(results_df)} records for {company}")
            return self._process_records(results_df)
        except Exception as e:
            logger.error(f"BigQuery failure for {company}: {e}")
            return CollectorResult(
                normalized_score=0.0,
                confidence=0.0,
                raw_value="Database query failed",
                metadata={"error": str(e)}
            )
