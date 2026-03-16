"""
Score Justification Generator.

Transforms retrieved evidence into ~150-word PE-style investment memo paragraphs,
one per AI maturity dimension, with inline citations from the source material.
Follows the class-based singleton service pattern used across the codebase.
"""
from __future__ import annotations

import structlog
from typing import Dict, List, Tuple

from app.models.rag import (
    CitedEvidence,
    Dimension,
    RetrievedDocument,
    ScoreJustification,
    ScoreLevel,
    TaskType,
)
from app.services.llm.router import ModelRouter

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Static dimension metadata
# ---------------------------------------------------------------------------

#: Human-readable rubric descriptions used in the LLM prompt (one per dimension).
DIMENSION_RUBRIC: Dict[Dimension, str] = {
    Dimension.DATA_INFRASTRUCTURE: (
        "Evaluates cloud data-platform maturity, ETL pipeline sophistication, "
        "data-lake / warehouse architecture, and readiness to serve ML workloads."
    ),
    Dimension.AI_GOVERNANCE: (
        "Assesses formal AI/ML governance policies, model-risk management, "
        "regulatory compliance posture, and responsible-AI frameworks."
    ),
    Dimension.TECHNOLOGY_STACK: (
        "Reviews ML infrastructure, GPU/compute availability, MLOps tooling, "
        "CI/CD pipelines for models, and modern DevOps practices."
    ),
    Dimension.TALENT: (
        "Measures AI/ML hiring velocity, engineering density, retention signals, "
        "and technical bench strength across data-science and AI roles."
    ),
    Dimension.LEADERSHIP: (
        "Evaluates executive AI awareness, board-level digital literacy, CDO/CAIO "
        "presence, and leadership commitment to AI transformation."
    ),
    Dimension.USE_CASE_PORTFOLIO: (
        "Catalogues live AI/ML applications, product integrations, "
        "revenue-generating models, and automation initiatives across business lines."
    ),
    Dimension.CULTURE: (
        "Captures employee innovation sentiment, agile/learning culture indicators, "
        "and AI-readiness signals from Glassdoor and internal surveys."
    ),
}

#: Scoring keywords surfaced in the justification model (dimension → keyword list).
DIMENSION_KEYWORDS: Dict[Dimension, List[str]] = {
    Dimension.DATA_INFRASTRUCTURE: [
        "data lake", "ETL", "Snowflake", "Databricks", "cloud", "pipeline", "warehouse",
    ],
    Dimension.AI_GOVERNANCE: [
        "governance", "compliance", "policy", "risk", "framework", "audit", "regulation",
    ],
    Dimension.TECHNOLOGY_STACK: [
        "MLOps", "Kubernetes", "GPU", "CI/CD", "infrastructure", "platform", "DevOps",
    ],
    Dimension.TALENT: [
        "hiring", "engineer", "data scientist", "ML", "talent", "headcount", "retention",
    ],
    Dimension.LEADERSHIP: [
        "CTO", "CDO", "CAIO", "executive", "board", "strategy", "vision",
    ],
    Dimension.USE_CASE_PORTFOLIO: [
        "model", "product", "automation", "deployed", "revenue", "application", "AI use case",
    ],
    Dimension.CULTURE: [
        "culture", "innovation", "agile", "employee", "Glassdoor", "rating", "sentiment",
    ],
}

#: Canonical retrieval queries used by the IC workflow when fetching dimension evidence.
DIMENSION_QUERIES: Dict[Dimension, str] = {
    Dimension.DATA_INFRASTRUCTURE: (
        "cloud data infrastructure ETL data lake warehouse pipeline analytics"
    ),
    Dimension.AI_GOVERNANCE: (
        "AI governance policy compliance regulation risk management framework"
    ),
    Dimension.TECHNOLOGY_STACK: (
        "machine learning infrastructure MLOps DevOps CI/CD technology stack"
    ),
    Dimension.TALENT: (
        "AI machine learning engineering hiring talent data scientist workforce"
    ),
    Dimension.LEADERSHIP: (
        "executive leadership CDO CTO AI strategy board digital transformation"
    ),
    Dimension.USE_CASE_PORTFOLIO: (
        "AI use cases deployed models applications automation revenue product"
    ),
    Dimension.CULTURE: (
        "innovation culture employee sentiment Glassdoor agile learning development"
    ),
}


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------

def score_to_level(score: float) -> Tuple[int, str]:
    """Map a 0-100 dimension score to (ScoreLevel int, label string)."""
    if score >= 80:
        return ScoreLevel.LEVEL_5, "Excellent"
    elif score >= 60:
        return ScoreLevel.LEVEL_4, "Good"
    elif score >= 40:
        return ScoreLevel.LEVEL_3, "Adequate"
    elif score >= 20:
        return ScoreLevel.LEVEL_2, "Developing"
    return ScoreLevel.LEVEL_1, "Nascent"


def derive_evidence_strength(evidence: List[RetrievedDocument]) -> str:
    """Return 'strong', 'moderate', or 'weak' based on evidence count."""
    n = len(evidence)
    if n >= 4:
        return "strong"
    if n >= 2:
        return "moderate"
    return "weak"


def approximate_confidence_interval(score: float, evidence_count: int) -> Tuple[float, float]:
    """
    Approximate 95 % CI using SEM-style logic that mirrors the CS3 scoring engine.
    A larger evidence corpus narrows the interval.
    """
    sem = max(2.0, 15.0 / (evidence_count ** 0.5)) if evidence_count > 0 else 15.0
    return (max(0.0, score - sem), min(100.0, score + sem))


def build_cited_evidence(docs: List[RetrievedDocument]) -> List[CitedEvidence]:
    """Convert RetrievedDocuments into CitedEvidence records (content capped at 500 chars)."""
    return [
        CitedEvidence(
            evidence_id=doc.doc_id,
            content=doc.content[:500],
            source_type=doc.metadata.get("source_type", "unknown"),
            source_url=doc.metadata.get("source_url"),
            confidence=float(doc.metadata.get("confidence", doc.score)),
            relevance_score=doc.score,
        )
        for doc in docs
    ]


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class JustificationGenerator:
    """
    Generates PE-style score justifications (~150 words) for each of the 7
    AI maturity dimensions, backed by citations from retrieved evidence.

    The generator routes all LLM calls through the shared ``ModelRouter``
    using ``TaskType.JUSTIFICATION_GENERATION`` (claude-3-5-sonnet primary,
    gpt-4o fallback), consistent with the model routing table in
    ``app/services/llm/router.py``.

    Usage::

        gen = JustificationGenerator(llm_router)
        justification = await gen.generate(
            company_id="AAPL",
            dimension=Dimension.TALENT,
            score=72.5,
            evidence=retrieved_docs,
        )
    """

    def __init__(self, llm_router: ModelRouter) -> None:
        self.llm_router = llm_router

    async def generate(
        self,
        company_id: str,
        dimension: Dimension,
        score: float,
        evidence: List[RetrievedDocument],
    ) -> ScoreJustification:
        """
        Produce a ``ScoreJustification`` for one dimension.

        Args:
            company_id: Ticker / company identifier (e.g. ``"AAPL"``).
            dimension: One of the seven AI maturity dimensions.
            score: Numeric score (0–100) for this dimension.
            evidence: Retrieved documents supporting the score.

        Returns:
            A fully populated :class:`~app.models.rag.ScoreJustification`.
        """
        level_int, level_name = score_to_level(score)
        rubric = DIMENSION_RUBRIC.get(dimension, "")
        keywords = DIMENSION_KEYWORDS.get(dimension, [])
        dim_label = dimension.value.replace("_", " ").title()

        # Build numbered evidence block for the prompt
        evidence_text = "\n".join(
            f"[{i + 1}] {d.content[:400]}" for i, d in enumerate(evidence)
        )

        system_prompt = (
            "You are a Senior Private Equity AI Analyst writing an investment memo. "
            "Your output must be exactly ~150 words: one professional, citation-rich "
            "paragraph assessing one AI maturity dimension for a target company. "
            "Cite evidence inline using [N] notation. "
            "End with a single sentence identifying the primary gap."
        )

        user_prompt = (
            f"Company: {company_id}\n"
            f"Dimension: {dim_label}\n"
            f"Score: {score:.1f}/100  ({level_name})\n"
            f"Rubric: {rubric}\n\n"
            f"Evidence:\n{evidence_text}\n\n"
            "Write the ~150-word PE investment memo paragraph now."
        )

        generated_summary = ""
        gaps_identified: List[str] = []

        try:
            response = await self.llm_router.complete(
                task=TaskType.JUSTIFICATION_GENERATION,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()

            # Heuristic: treat the final sentence as the identified gap
            sentences = [s.strip() for s in raw.split(".") if s.strip()]
            if len(sentences) > 1:
                generated_summary = ". ".join(sentences[:-1]) + "."
                gaps_identified = [sentences[-1] + "."]
            else:
                generated_summary = raw

            logger.info(
                "justification_generated",
                company=company_id,
                dimension=dimension.value,
                score=score,
                evidence_count=len(evidence),
            )

        except Exception as exc:
            logger.error(
                "justification_generation_failed",
                company=company_id,
                dimension=dimension.value,
                error=str(exc),
            )
            generated_summary = (
                f"Unable to generate narrative for {dim_label} "
                f"(score {score:.1f}). Manual review required."
            )

        return ScoreJustification(
            company_id=company_id,
            dimension=dimension,
            score=score,
            level=level_int,
            level_name=level_name,
            confidence_interval=approximate_confidence_interval(score, len(evidence)),
            rubric_criteria=rubric,
            rubric_keywords=keywords,
            supporting_evidence=build_cited_evidence(evidence),
            gaps_identified=gaps_identified,
            generated_summary=generated_summary,
            evidence_strength=derive_evidence_strength(evidence),
        )
