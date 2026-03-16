import os
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from google.cloud import bigquery

# -----------------------------
# Logging configuration
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class PatentSignalV3:
    # Restoring the AI categories and keywords from v2 for maximum coverage
    AI_PATENT_KEYWORDS = [
        "machine learning", "neural network", "deep learning",
        "artificial intelligence", "natural language processing",
        "computer vision", "reinforcement learning", "pattern recognition",
        "autonomous", "predictive modeling", "generative model", "transformer network", 
        "llm", "gpt", "model training"
    ]

    def __init__(self, project_id: Optional[str] = None):
        self.client = bigquery.Client(project=project_id)
        self.output_file = "patent_signals_v3.csv"
        
        # Mapping CPCs to the 5/2/10 scoring categories
        self.INNOVATION_MAP = {
            "autonomy": ["G05D", "B60W", "G01S", "G05B"],
            "ai_ml": ["G06N", "G06K", "G06F18"],
            "computer_vision": ["G06T", "G06V", "G01B"],
            "electrification": ["H02J", "H01M", "B60L", "H01T"],
            "iot_digital": ["G06Q", "H04L", "H04W", "G07C"]
        }

    def generate_query(self, company_name: str, years: int = 5) -> str:
        """
        PREDICTABLE 33GB QUERY.
        Pulls all company patents for the timeframe; filtering is done in Python
        to avoid unpredictable BQ 'Where' clause scan costs.
        """
        # Clean company name for BigQuery (remove common suffixes)
        clean_company = company_name.upper()
        suffixes = [
            " INC.", " INC", " CORP.", " CORP", " LTD.", " LTD", 
            " GROUP", " LLC", " PLC", " & COMPANY", " & CO", " CO.", " CO"
        ]
        for suffix in suffixes:
            if suffix in clean_company:
                clean_company = clean_company.split(suffix)[0].strip()
        
        # Final safety check: if name is still very long and has " & ", split it
        if " & " in clean_company:
            clean_company = clean_company.split(" & ")[0].strip()
        
        date_cutoff = (datetime.now().year - years) * 10000 + 101
        
        query = f"""
        SELECT 
            p.publication_number,
            ANY_VALUE(p.title_localized[SAFE_OFFSET(0)].text) as title,
            ANY_VALUE(p.filing_date) as filing_date,
            COUNT(DISTINCT cit.publication_number) as citation_count,
            ARRAY_AGG(DISTINCT c.code IGNORE NULLS) as cpc_codes
        FROM `bigquery-public-data.patents.publications` AS p
        LEFT JOIN UNNEST(p.assignee_harmonized) AS a
        LEFT JOIN UNNEST(p.cpc) AS c
        LEFT JOIN UNNEST(p.citation) AS cit
        WHERE a.name LIKE '{clean_company}%'
          AND p.filing_date > {date_cutoff}
        GROUP BY p.publication_number
        """
        return query

    def score_innovation(self, company_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        STRICT 5/2/10 SCORING WITH REFINED AI DETECTION.
        """
        if df.empty:
            return {"company_name": company_name, "normalized_score": 0, "status": "No patents found"}

        now = datetime.now()
        # Filing date is YYYYMMDD integer in BQ
        last_year_cutoff = int((now - timedelta(days=365)).strftime("%Y%m%d"))
        
        ai_patents_count = 0
        recent_ai_count = 0
        total_citations = 0
        active_categories = set()
        
        for _, row in df.iterrows():
            title = str(row['title'] or "").lower()
            codes = row['cpc_codes']
            if codes is None or (hasattr(codes, 'size') and codes.size == 0):
                codes = []

            # AI Detection logic (Keywords or CPC)
            is_ai = False
            if any(kw in title for kw in self.AI_PATENT_KEYWORDS):
                is_ai = True
            
            patent_cats = []
            for cat, prefixes in self.INNOVATION_MAP.items():
                if any(any(str(code).startswith(pref) for pref in prefixes) for code in codes):
                    is_ai = True
                    patent_cats.append(cat)

            if is_ai:
                ai_patents_count += 1
                total_citations += int(row['citation_count'] or 0)
                active_categories.update(patent_cats)
                if int(row['filing_date'] or 0) > last_year_cutoff:
                    recent_ai_count += 1

        # 5/2/10 Rule Calculation
        patent_volume_score = min(ai_patents_count * 5, 50) 
        recency_bonus = min(recent_ai_count * 2, 20)        
        diversity_score = min(len(active_categories) * 10, 30) 
        
        final_score = patent_volume_score + recency_bonus + diversity_score

        return {
            "company_name": company_name,
            "category": "INNOVATION_SIGNAL",
            "source": "BIGQUERY",
            "normalized_score": round(final_score, 1),
            "total_company_patents": len(df),
            "identified_ai_patents": ai_patents_count,
            "recent_ai_patents": recent_ai_count,
            "tech_diversity": len(active_categories),
            "categories": ",".join(sorted(active_categories)),
            "total_ai_citations": total_citations,
            "top_impact_citations": int(df['citation_count'].max() if not df.empty else 0)
        }

    def run(self, company_name: str, years: int = 5):
        logging.info(f"Running Analysis for {company_name}...")
        query = self.generate_query(company_name, years)
        
        try:
            df = self.client.query(query).to_dataframe()
            logging.info(f"Retrieved {len(df)} total patents.")
            
            result = self.score_innovation(company_name, df)
            logging.info(f"Result: {result}")
            
            pd.DataFrame([result]).to_csv(self.output_file, mode='a', index=False, header=not os.path.exists(self.output_file))
            return result
        except Exception as e:
            logging.error(f"BQ Error: {e}")
            return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--project", required=True)
    args = parser.parse_args()

    collector = PatentSignalV3(project_id=args.project)
    collector.run(args.company)
