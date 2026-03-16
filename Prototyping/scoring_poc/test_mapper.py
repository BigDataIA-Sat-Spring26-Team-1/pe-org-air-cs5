from decimal import Decimal
from evidence_mapper import EvidenceMapper, EvidenceScore, SignalSource, Dimension

def main():
    print("=== Testing Evidence Mapper Logic ===\n")

    # 1. Create Simulated Evidence (as if from Snowflake/AWS)
    evidence = [
        # Strong Hiring Signal -> Maps to Talent, Tech, Culture
        EvidenceScore(
            source=SignalSource.TECHNOLOGY_HIRING,
            raw_score=Decimal("85.0"),
            confidence=Decimal("0.9"),
            evidence_count=150,
            metadata={"top_role": "Machine Learning Engineer"}
        ),
        # Strong Innovation -> Maps to Tech, Use Case
        EvidenceScore(
            source=SignalSource.INNOVATION_ACTIVITY,
            raw_score=Decimal("90.0"),
            confidence=Decimal("0.8"),
            evidence_count=12,
            metadata={"patents": 5}
        ),
        # Weak Leadership Signals (Sparse/Low)
        EvidenceScore(
            source=SignalSource.LEADERSHIP_SIGNALS,
            raw_score=Decimal("40.0"),
            confidence=Decimal("0.6"),
            evidence_count=2,
            metadata={}
        ),
        # New CS3 Signal: Glassdoor
        EvidenceScore(
            source=SignalSource.GLASSDOOR_REVIEWS,
            raw_score=Decimal("65.0"),  # From previous POC
            confidence=Decimal("0.7"),
            evidence_count=6,
            metadata={}
        )
    ]

    mapper = EvidenceMapper()
    
    # 2. Run Mapping
    scores = mapper.map_evidence_to_dimensions(evidence)
    
    # 3. Print Results
    print(f"{'DIMENSION':<25} | {'SCORE':<6} | {'CONF':<5} | {'SOURCES'}")
    print("-" * 70)
    
    for dim in Dimension:
        ds = scores[dim]
        # Just simple string join for sources
        srcs = ", ".join([s.name.replace("SignalSource.", "") for s in ds.contributing_sources])
        print(f"{dim.value:<25} | {ds.score:<6} | {ds.confidence:<5} | {srcs}")

    # 4. Property Tests (Simple Verification)
    print("\n=== Property Tests ===")
    
    # Test 1: All 7 dimensions exist?
    assert len(scores) == 7, "❌ Not all 7 dimensions returned!"
    print(f"✅ All 7 dimensions present.")
    
    # Test 2: Bounded [0, 100]?
    for dim, ds in scores.items():
        assert 0 <= ds.score <= 100, f"❌ Score out of bounds for {dim}: {ds.score}"
    print(f"✅ All scores bounded [0, 100].")

    # Test 3: Default is 50.0?
    # Create empty evidence list
    empty_scores = mapper.map_evidence_to_dimensions([])
    for dim, ds in empty_scores.items():
        assert ds.score == 50.0, f"❌ Default score incorrect for {dim}: {ds.score}"
    print(f"✅ Empty evidence defaults to 50.0.")

    print("\n✅ Evidence Mapping Logic Verified.")

if __name__ == "__main__":
    main()
