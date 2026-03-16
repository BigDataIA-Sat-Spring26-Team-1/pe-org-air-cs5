import os
import sys
from decimal import Decimal
from typing import List

# Import our poc components locally
from snowflake_client import SnowflakeClient
from evidence_mapper import EvidenceMapper, EvidenceScore, SignalSource, Dimension

def verify_data(ticker: str = "NVDA"):
    print(f"=== VERIFYING REAL DATA FROM SNOWFLAKE FOR: {ticker} ===\n")
    
    client = SnowflakeClient()
    
    # 1. Fetch Company
    company = client.fetch_company_by_ticker(ticker)
    if not company:
        print(f"❌ Company {ticker} not found in Snowflake!")
        return
    
    company_id = company['ID'] if 'ID' in company else company.get('id')
    company_name = company['NAME'] if 'NAME' in company else company.get('name')
    market_cap = company['MARKET_CAP'] if 'MARKET_CAP' in company else company.get('market_cap', 0)
    
    print(f"✅ Found Company: {company_name} (ID: {company_id})")
    print(f"   Market Cap Found: {market_cap}")

    # 2. Fetch Signals
    signals = client.fetch_external_signals(company_id)
    print(f"✅ Found {len(signals)} external signals in Snowflake.")
    
    if len(signals) == 0:
        print("Empty signals in Snowflake. Cannot verify mapping logic with real data.")
        return

    # 3. Map to EvidenceScore
    evidence = []
    # Map of Snowflake categories to SignalSource enum members
    category_map = {
        "technology_hiring": SignalSource.TECHNOLOGY_HIRING,
        "innovation_activity": SignalSource.INNOVATION_ACTIVITY,
        "digital_presence": SignalSource.DIGITAL_PRESENCE,
        "leadership_signals": SignalSource.LEADERSHIP_SIGNALS,
        "sec_item_1": SignalSource.SEC_ITEM_1,
        "sec_item_1a": SignalSource.SEC_ITEM_1A,
        "sec_item_7": SignalSource.SEC_ITEM_7
    }

    print("\nProcessing Signals:")
    for s in signals:
        cat_key = (s['CATEGORY'] if 'CATEGORY' in s else s.get('category', '')).lower()
        enum_src = category_map.get(cat_key)
        
        # Keys might be uppercase in Snowflake result set
        norm_score = s['NORMALIZED_SCORE'] if 'NORMALIZED_SCORE' in s else s.get('normalized_score', 0)
        confidence = s['CONFIDENCE'] if 'CONFIDENCE' in s else s.get('confidence', 0.5)
        
        if enum_src:
            evidence.append(EvidenceScore(
                source=enum_src,
                raw_score=Decimal(str(norm_score)),
                confidence=Decimal(str(confidence)),
                evidence_count=1
            ))
            print(f"   - Match: {cat_key} | Score: {norm_score} | Conf: {confidence}")
        else:
            print(f"   - Skip: {cat_key} (Not in mapping matrix)")

    if not evidence:
        print("\n❌ No signals could be mapped. Check if Table 1 categories match Snowflake data.")
        return

    # 4. Run Evidence Mapper
    mapper = EvidenceMapper()
    dim_scores = mapper.map_evidence_to_dimensions(evidence)
    
    print("\n" + "="*60)
    print(f" RESULTS: {company_name} OVER REAL DATA")
    print("="*60)
    print(f"{'DIMENSION':<25} | {'SCORE':<7} | {'CONF':<6}")
    print("-" * 60)
    for dim in Dimension:
        ds = dim_scores[dim]
        # Format score as string to avoid Decimal printing issues
        score_str = f"{float(ds.score):.2f}"
        conf_str = f"{float(ds.confidence):.2f}"
        print(f"{dim.value:<25} | {score_str:<7} | {conf_str:<6}")
    print("="*60)

if __name__ == "__main__":
    # Ensure ticker is passed if desired
    ticker_to_check = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    verify_data(ticker_to_check)
