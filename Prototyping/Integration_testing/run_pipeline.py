from scoring_engine import (
    ScoringIntegrationService, 
    EvidenceScore, 
    SignalSource, 
    JobAnalysis, 
    BoardMember, 
    Dimension
)
from decimal import Decimal
import json

def run_test():
    service = ScoringIntegrationService()
    
    # --- TEST 1: JPMORGAN CHASE ---
    # Expected: 65-75, PF: +0.5, TC: 0.18
    # We simulate data that leads to TC ~0.18 and PF ~0.5
    jpm_evidence = [
        EvidenceScore(SignalSource.TECHNOLOGY_HIRING, Decimal("75"), Decimal("0.9"), 120),
        EvidenceScore(SignalSource.INNOVATION_ACTIVITY, Decimal("65"), Decimal("0.8"), 45),
        EvidenceScore(SignalSource.LEADERSHIP_SIGNALS, Decimal("70"), Decimal("0.85"), 12),
        EvidenceScore(SignalSource.SEC_ITEM_1, Decimal("68"), Decimal("0.95"), 1),
        EvidenceScore(SignalSource.GLASSDOOR_REVIEWS, Decimal("72"), Decimal("0.7"), 850)
    ]
    
    jpm_jobs = JobAnalysis(
        total_ai_jobs=120,
        senior_ai_jobs=50, # High leadership ratio
        mid_ai_jobs=50,
        entry_ai_jobs=20,
        unique_skills={"Python", "ML", "AWS", "SQL", "Spark", "PyTorch", "Java", "Kubernetes", "Docker", "NLP", "LLM", "Hadoop"} # 12 skills
    )
    
    jpm_board = [
        BoardMember("Jamie Dimon", "CEO", "Leadership expert", False, 18, ["Executive"]),
        BoardMember("Lori Beer", "Global CIO", "Technology and AI strategy expert", False, 7, ["Technology"])
    ]
    
    jpm_results = service.score_company(
        ticker="JPM",
        sector="financial_services",
        market_cap_p=0.9, # Large bank
        evidence=jpm_evidence,
        job_analysis=jpm_jobs,
        board_members=jpm_board,
        board_committees=["Technology Committee", "Risk Committee"],
        glassdoor_stats={'mentions': 15, 'reviews': 850}
    )
    
    # --- TEST 2: WALMART ---
    # Expected: 55-65, PF: +0.3, TC: 0.20
    wmt_evidence = [
        EvidenceScore(SignalSource.TECHNOLOGY_HIRING, Decimal("60"), Decimal("0.85"), 80),
        EvidenceScore(SignalSource.INNOVATION_ACTIVITY, Decimal("55"), Decimal("0.75"), 20),
        EvidenceScore(SignalSource.LEADERSHIP_SIGNALS, Decimal("62"), Decimal("0.8"), 8),
        EvidenceScore(SignalSource.SEC_ITEM_1, Decimal("58"), Decimal("0.9"), 1),
        EvidenceScore(SignalSource.GLASSDOOR_REVIEWS, Decimal("55"), Decimal("0.7"), 1200)
    ]
    
    wmt_jobs = JobAnalysis(
        total_ai_jobs=80,
        senior_ai_jobs=20,
        mid_ai_jobs=40,
        entry_ai_jobs=20,
        unique_skills={"Python", "SQL", "Cloud", "Supply Chain AI", "Java"} # 5 skills
    )
    
    wmt_board = [
        BoardMember("Doug McMillon", "CEO", "Retail expert", False, 10, ["Executive"]),
        BoardMember("Independent Director", "Director", "Supply chain and digital", True, 5, ["Audit"])
    ]
    
    wmt_results = service.score_company(
        ticker="WMT",
        sector="retail",
        market_cap_p=0.85, # Large retailer
        evidence=wmt_evidence,
        job_analysis=wmt_jobs,
        board_members=wmt_board,
        board_committees=["Audit Committee"],
        glassdoor_stats={'mentions': 40, 'reviews': 1200}
    )

    print("\n" + "="*50)
    print("INTEGRATION PIPELINE SIMULATION RESULTS")
    print("="*50)
    
    for res in [jpm_results, wmt_results]:
        print(f"\n[Ticker: {res['ticker']}]")
        print(f"Final Org-AI-R Score: {res['final_score']:.2f}")
        print(f"  - Vertical Readiness (V^R): {res['vr_score']:.2f}")
        print(f"  - Horizontal Readiness (H^R): {res['hr_score']:.2f}")
        print(f"  - Synergy Score: {res['synergy_score']:.2f}")
        print(f"  - Talent Concentration (TC): {res['talent_concentration']:.2f}")
        print(f"  - Position Factor (PF): {res['position_factor']:.2f}")
        print(f"  - Confidence: {res['confidence']:.2f}")
        print(f"Dimension Breakdown:")
        for dim, score in res['dimension_scores'].items():
            print(f"  * {dim:20}: {score}")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_test()
