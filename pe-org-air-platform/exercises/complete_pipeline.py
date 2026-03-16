"""
Complete Pipeline Exercise: Why did NVIDIA score 78 on Data Infrastructure?

Prerequisites: CS1, CS2, CS3 APIs running with NVDA data
"""
import asyncio
import os
import sys

# Ensure app modules are importable
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))
# Also add the root if running locally
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from services.integration.cs1_client import CS1Client
from services.integration.cs2_client import CS2Client
from services.integration.cs3_client import CS3Client
from models.enums import Dimension
from services.retrieval.hybrid import HybridRetriever
from services.retrieval.dimension_mapper import DimensionMapper
from services.search.vector_store import VectorStore
from services.justification.generator import JustificationGenerator

async def exercise_nvda_justification():
    """Generate score justification for NVIDIA Data Infrastructure."""

    print("="*60)
    print("EXERCISE: NVIDIA Data Infrastructure Score Justification")
    print("="*60)

    # 1. Verify company in CS1
    cs1 = CS1Client()
    company_data = await cs1.get_company("NVDA")
    print(f"\n[CS1] Company: {company_data.get('name', 'NVIDIA')}")
    print(f" Sector: {company_data.get('sector', 'technology')}")
    print(f" Market Cap Percentile: {company_data.get('market_cap_percentile', 0.98):.2f}")

    # 2. Fetch CS3 score
    cs3 = CS3Client()
    score = await cs3.get_dimension_score("NVDA", Dimension.DATA_INFRASTRUCTURE)
    print(f"\n[CS3] Data Infrastructure Score: {score.score:.1f}")
    print(f" Level: {score.level.value} ({score.level.name_label})")
    print(f" 95% CI: [{score.confidence_interval[0]:.1f}, {score.confidence_interval[1]:.1f}]")

    # 3. Get rubric for the level
    rubrics = await cs3.get_rubric(Dimension.DATA_INFRASTRUCTURE, score.level)
    rubric = rubrics[0] if rubrics else None
    print(f"\n[CS3] Level {score.level.value} Rubric:")
    if rubric:
        print(f" {rubric.criteria_text[:100]}...")
        print(f" Keywords: {rubric.keywords[:5]}")

    # 4. Fetch and index CS2 evidence
    cs2 = CS2Client()
    evidence_list = await cs2.get_evidence("NVDA")
    print(f"\n[CS2] Total evidence items: {len(evidence_list)}")

    mapper = DimensionMapper()
    # Note: Using the actual persistent vector store for this exercise
    vector_store = VectorStore(persist_dir="/opt/airflow/app_code/data/chroma")
    retriever = HybridRetriever(vector_store=vector_store)

    # Re-indexing for parity with simulation (optional if already ingested)
    # Formatted for retriever
    docs = []
    for e in evidence_list:
        primary_dim = mapper.get_primary_dimension(e.signal_category, e.source_type)
        docs.append({
            "doc_id": e.evidence_id,
            "content": e.content,
            "metadata": {
                "company_id": e.company_id,
                "source_type": e.source_type.value,
                "dimension": primary_dim.value,
                "confidence": e.confidence,
            }
        })
    
    retriever.index_documents(docs)
    print(f"[CS4] Indexed {len(docs)} documents")

    # 5. Generate justification
    generator = JustificationGenerator()
    justification = await generator.generate(
        company_id="NVDA", 
        dimension=Dimension.DATA_INFRASTRUCTURE,
        score=score.score,
        evidence=[] # Generator will retrieve itself
    )

    # 6. Display results
    print("\n" + "="*60)
    print("SCORE JUSTIFICATION")
    print("="*60)
    print(f"\nCompany: {company_data.get('name')} (NVDA)")
    print(f"Dimension: Data Infrastructure")
    print(f"Score: {justification.score:.0f}/100 (Level {justification.level.value} - {justification.level_name})")
    print(f"Confidence CI: [{justification.confidence_interval[0]:.0f}, {justification.confidence_interval[1]:.0f}]")

    print(f"\nRubric Match:")
    print(f" {justification.rubric_criteria[:200]}...")

    print(f"\nSupporting Evidence ({len(justification.supporting_evidence)} items):")
    for i, e in enumerate(justification.supporting_evidence, 1):
        print(f" {i}. [{e.source_type}] (conf={e.confidence:.2f})")
        print(f" {e.content[:100]}...")
        if e.matched_keywords:
            print(f" Matched: {e.matched_keywords}")

    print(f"\nGaps Identified:")
    for gap in justification.gaps_identified:
        print(f" - {gap}")

    print(f"\nEvidence Strength: {justification.evidence_strength.upper()}")

    print(f"\nGenerated Summary:")
    print(f" {justification.generated_summary}")

    # Cleanup (not strictly needed in script but good practice)
    await cs1.close()
    await cs2.close()
    await cs3.close()

if __name__ == "__main__":
    asyncio.run(exercise_nvda_justification())
