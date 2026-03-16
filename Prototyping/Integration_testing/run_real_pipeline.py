import sys
import os
from db_client import SnowflakeClient
from scoring_engine import (
    ScoringIntegrationService, 
    EvidenceScore, 
    SignalSource, 
    JobAnalysis, 
    BoardMember as SMBoardMember,
    Dimension
)
# Import real board analyzer from platform
sys.path.append(os.path.abspath("../../pe-org-air-platform"))
from app.pipelines.board_analyzer import BoardCompositionAnalyzer
from decimal import Decimal

def main(ticker: str):
    env_path = "../../pe-org-air-platform/.env"
    if not os.path.exists(env_path):
        print(f"Error: .env not found at {env_path}")
        return

    db = SnowflakeClient(env_path)
    service = ScoringIntegrationService()
    board_analyzer = BoardCompositionAnalyzer()

    print(f"\n>>> Starting Advanced Integration Pipeline Simulation for {ticker}")
    
    # 1. Fetch Company
    company = db.fetch_company(ticker)
    if not company:
        print(f"Error: Company {ticker} not found.")
        db.close()
        return
    print(f"Fetched Company: {company['NAME']}")

    # 2. Fetch Evidence (External Signals)
    signals = db.fetch_evidence(company['ID'])
    print(f"Found {len(signals)} pre-calculated external signals.")
    evidence_scores = []
    for s in signals:
        try:
            # We skip Digital Presence if it's 0 to trigger our new Estimator
            if s['CATEGORY'] == 'digital_presence' and float(s['NORMALIZED_SCORE'] or 0) == 0:
                print("Skipping 0.0 Digital Presence to trigger Job-based Estimation...")
                continue
            evidence_scores.append(EvidenceScore(
                source=SignalSource(s['CATEGORY']),
                raw_score=Decimal(str(s['NORMALIZED_SCORE'] or 0)),
                confidence=Decimal(str(s['CONFIDENCE'] or 0.5)),
                evidence_count=1
            ))
        except ValueError: continue

    # 3. Analyze Talent & Tech Footprint (Digital Presence Fix)
    jobs = db.fetch_job_descriptions(company['ID'])
    print(f"Analyzing {len(jobs)} Job Descriptions for Talent & Tech Markers...")
    
    combined_job_text = " ".join([(j['DESCRIPTION'] or "") for j in jobs])
    senior_ai = sum(1 for j in jobs if any(kw in (j['TITLE'] or "").lower() for kw in ["principal", "staff", "director", "vp", "head"]))
    unique_skills = set()
    for j in jobs:
        desc = (j['DESCRIPTION'] or "").lower()
        for s in ["python", "ml", "aws", "snowflake", "pytorch", "spark"]:
            if s in desc: unique_skills.add(s)

    job_analysis = JobAnalysis(
        total_ai_jobs=len(jobs),
        senior_ai_jobs=senior_ai,
        mid_ai_jobs=max(0, len(jobs) - senior_ai),
        entry_ai_jobs=0,
        unique_skills=unique_skills,
        raw_job_text=combined_job_text
    )

    # 4. SEC Item Scoring (Text-Based Rubrics)
    sec_chunks = db.fetch_sec_chunks(ticker, limit=50) # INCREASED LIMIT
    print(f"Found {len(sec_chunks)} SEC Document Chunks for Rubric Scoring.")
    # Combine text for scoring
    sec_text = " ".join([c['CHUNK_TEXT'] for c in sec_chunks])
    
    # Item 1 -> Use Case Dimension
    sec_1_score = service.rubric_scorer.score_text(sec_text, Dimension.USE_CASE_PORTFOLIO)
    evidence_scores.append(EvidenceScore(SignalSource.SEC_ITEM_1, sec_1_score, Decimal("0.9"), 1))
    
    # Item 1A -> Governance Dimension
    sec_1a_score = service.rubric_scorer.score_text(sec_text, Dimension.AI_GOVERNANCE)
    evidence_scores.append(EvidenceScore(SignalSource.SEC_ITEM_1A, sec_1a_score, Decimal("0.9"), 1))

    # 5. Culture & Glassdoor
    culture_data = db.fetch_culture_scores(ticker)
    if culture_data:
        avg_culture = (Decimal(str(culture_data['INNOVATION_SCORE'] or 0)) + Decimal(str(culture_data['AI_AWARENESS_SCORE'] or 0)) + Decimal(str(culture_data['CHANGE_READINESS_SCORE'] or 0))) / Decimal("3")
        evidence_scores.append(EvidenceScore(SignalSource.GLASSDOOR_REVIEWS, avg_culture, Decimal("0.8"), culture_data['REVIEW_COUNT'] or 1))

    # 6. Real Board Data from SEC-API
    print("Fetching REAL Board Data from SEC-API.io...")
    members, committees = board_analyzer.fetch_board_data(ticker)
    
    # Run real analysis logic
    gov_signal = board_analyzer.analyze_board(company['ID'], ticker, members, committees)
    print(f"Board Analysis Score: {gov_signal.governance_score} (Confidence: {gov_signal.confidence})")
    
    # Add to evidence (Replacing the BOARD_COMPOSITION that service.score_company adds)
    evidence_scores.append(EvidenceScore(SignalSource.BOARD_COMPOSITION, Decimal(str(gov_signal.governance_score)), Decimal(str(gov_signal.confidence)), 1))

    # 7. Run Final Scoring
    results = service.score_company(
        ticker=ticker,
        sector="financial_services" if ticker == "JPM" else "retail",
        market_cap_p=0.9,
        evidence=evidence_scores,
        job_analysis=job_analysis,
        board_members=[], # Already handled via evidence
        board_committees=[],
        glassdoor_stats={'reviews': culture_data['REVIEW_COUNT'] if culture_data else 20, 'mentions': 5}
    )

    print("\n" + "="*50)
    print(f"ADVANCED ASSESSMENT FOR {ticker}")
    print("="*50)
    print(f"Org-AI-R Score: {results['final_score']:.2f}")
    print(f"V^R: {results['vr_score']:.2f} | H^R: {results['hr_score']:.2f} | Synergy: {results['synergy_score']:.2f}")
    print(f"Position Factor (PF): {results['position_factor']:.2f}")
    print("-" * 50)
    print("Dimension Breakdown:")
    for dim, score in results['dimension_scores'].items():
        print(f"  - {dim:20}: {score}")
    print("="*50 + "\n")
    
    print("Note on SEC Scoring: Values for SEC_ITEM_1 and 1A were derived via Rubric-Matching ")
    print("against Keyword-Maturity criteria (Level 1-5).")
    print("Note on Board Signaling: Scored using REAL data from SEC-API.io via Directors API.")

    db.close()

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "JPM"
    main(target)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "JPM"
    main(target)
