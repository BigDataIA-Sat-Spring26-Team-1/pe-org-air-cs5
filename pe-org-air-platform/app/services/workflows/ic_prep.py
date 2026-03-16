from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.rag import (
    Company,
    CompanyAssessment,
    Dimension,
    DimensionScore,
    ICMeetingPackage,
    ScoreJustification,
    ScoreLevel,
    Sector,
    TaskType,
)
from app.services.justification.generator import (
    DIMENSION_QUERIES,
    JustificationGenerator,
    approximate_confidence_interval,
    score_to_level,
)
from app.services.llm.router import ModelRouter
from app.services.retrieval.hybrid import HybridRetriever
from app.services.snowflake import db

logger = structlog.get_logger()

# Ordered list of all 7 dimensions for consistent iteration
ALL_DIMENSIONS: List[Dimension] = list(Dimension)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_company_model(ticker: str, row: Optional[Dict[str, Any]]) -> Company:
    """
    Construct a :class:`~app.models.rag.Company` from a Snowflake row.
    Falls back to sensible defaults for columns that may be absent.
    """
    if not row:
        return Company(
            company_id=ticker.upper(),
            ticker=ticker.upper(),
            name=ticker.upper(),
            sector=Sector.BUSINESS_SERVICES,
            sub_sector="Unknown",
            market_cap_percentile=0.5,
            revenue_millions=0.0,
            employee_count=0,
            fiscal_year_end="12/31",
        )

    # Attempt to map the Snowflake sector string to the Sector enum
    raw_sector = str(row.get("sector", "")).lower().replace(" ", "_")
    try:
        sector = Sector(raw_sector)
    except ValueError:
        sector = Sector.BUSINESS_SERVICES

    return Company(
        company_id=str(row.get("id", ticker.upper())),
        ticker=ticker.upper(),
        name=str(row.get("name", ticker.upper())),
        sector=sector,
        sub_sector=str(row.get("sub_sector", "Unknown")),
        market_cap_percentile=_safe_float(row.get("market_cap_percentile"), 0.5),
        revenue_millions=_safe_float(row.get("revenue_millions"), 0.0),
        employee_count=int(_safe_float(row.get("employee_count"), 0)),
        fiscal_year_end=str(row.get("fiscal_year_end", "12/31")),
    )


def _estimate_dimension_score(evidence_count: int, avg_relevance: float) -> float:
    """
    Lightweight heuristic score when no persisted assessment exists.
    Maps evidence density and relevance to a 0-100 scale.
    """
    base = min(evidence_count * 12.0, 60.0)   # up to 60 pts from quantity
    boost = avg_relevance * 40.0               # up to 40 pts from quality
    return round(min(base + boost, 100.0), 1)


def _build_dimension_score(
    dimension: Dimension,
    score: float,
    evidence_count: int,
) -> DimensionScore:
    """Build a :class:`~app.models.rag.DimensionScore` from a numeric score."""
    level_int, _ = score_to_level(score)
    try:
        level = ScoreLevel(level_int)
    except ValueError:
        level = ScoreLevel.LEVEL_1

    return DimensionScore(
        dimension=dimension,
        score=score,
        level=level,
        confidence_interval=approximate_confidence_interval(score, evidence_count),
        evidence_count=evidence_count,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


def _derive_avg_evidence_strength(
    justifications: Dict[Dimension, ScoreJustification],
) -> str:
    """Aggregate per-dimension evidence strength into a single label."""
    mapping = {"strong": 2, "moderate": 1, "weak": 0}
    values = [mapping.get(j.evidence_strength, 0) for j in justifications.values()]
    if not values:
        return "weak"
    avg = sum(values) / len(values)
    if avg >= 1.5:
        return "strong"
    if avg >= 0.75:
        return "moderate"
    return "weak"


class ICPrepWorkflow:


    def __init__(
        self,
        retriever: HybridRetriever,
        justification_generator: JustificationGenerator,
        llm_router: ModelRouter,
    ) -> None:
        self.retriever = retriever
        self.justification_generator = justification_generator
        self.llm_router = llm_router

    async def generate_meeting_package(
        self,
        ticker: str,
        top_k: int = 5,
    ) -> ICMeetingPackage:
     
    
        ticker = ticker.upper()
        logger.info("ic_prep_started", ticker=ticker, top_k=top_k)

        # 1. Company information
        company_row = await db.fetch_company_by_ticker(ticker)
        company = _build_company_model(ticker, company_row)

        # 2. Try to load the latest persisted assessment scores
        persisted_scores = await self._load_persisted_scores(
            company_row.get("id") if company_row else None
        )

        # 3. Retrieve evidence for each dimension concurrently
        evidence_map = await self._retrieve_all_dimensions(ticker, top_k)

        # Validate that we have at least some evidence
        total_evidence = sum(len(v) for v in evidence_map.values())
        if total_evidence == 0:
            raise ValueError(
                f"No indexed data found for {ticker}. "
                "Please run /api/v1/rag/ingest first."
            )

        # 4. Compute dimension scores (persisted > estimated from evidence)
        dimension_scores: Dict[Dimension, DimensionScore] = {}
        for dim in ALL_DIMENSIONS:
            docs = evidence_map.get(dim, [])
            if dim in persisted_scores:
                score = persisted_scores[dim]
            else:
                avg_rel = (
                    sum(d.score for d in docs) / len(docs) if docs else 0.0
                )
                score = _estimate_dimension_score(len(docs), avg_rel)
            dimension_scores[dim] = _build_dimension_score(dim, score, len(docs))

        # 5. Generate per-dimension justifications concurrently
        justifications = await self._generate_all_justifications(
            ticker, dimension_scores, evidence_map
        )

        # 6. Compute composite assessment scores
        assessment = self._build_assessment(ticker, dimension_scores, company)

        # 7. Synthesise executive memo via LLM
        exec_parts = await self._synthesise_executive_memo(
            ticker, company, assessment, justifications
        )

        total_evidence_count = sum(
            len(j.supporting_evidence) for j in justifications.values()
        )

        logger.info(
            "ic_prep_completed",
            ticker=ticker,
            dimensions=len(justifications),
            total_evidence=total_evidence_count,
        )

        return ICMeetingPackage(
            company=company,
            assessment=assessment,
            dimension_justifications=justifications,
            executive_summary=exec_parts["executive_summary"],
            key_strengths=exec_parts["key_strengths"],
            key_gaps=exec_parts["key_gaps"],
            risk_factors=exec_parts["risk_factors"],
            recommendation=exec_parts["recommendation"],
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_evidence_count=total_evidence_count,
            avg_evidence_strength=_derive_avg_evidence_strength(justifications),
        )

    async def _load_persisted_scores(
        self, company_id: Optional[str]
    ) -> Dict[Dimension, float]:
       
        if not company_id:
            return {}
        try:
            rows = await db.fetch_all(
                """
                SELECT a.id, a.v_r_score
                FROM   assessments a
                WHERE  a.company_id = %s
                ORDER  BY a.created_at DESC
                LIMIT  1
                """,
                (company_id,),
            )
            if not rows:
                return {}

            assessment_id = rows[0].get("id")
            dim_rows = await db.fetch_dimension_scores(assessment_id)

            scores: Dict[Dimension, float] = {}
            for r in dim_rows:
                try:
                    dim = Dimension(r.get("dimension", "").lower())
                    scores[dim] = _safe_float(r.get("score"), 0.0)
                except ValueError:
                    pass
            return scores

        except Exception as exc:
            logger.warning("persisted_scores_unavailable", error=str(exc))
            return {}

    async def _retrieve_all_dimensions(
        self, ticker: str, top_k: int
    ) -> Dict[Dimension, List[Any]]:
        """
        Run evidence retrieval for all 7 dimensions concurrently.
        Returns a mapping of dimension → list of RetrievedDocument.
        """
        filter_meta = {"company_id": ticker}

        async def _retrieve_one(dim: Dimension) -> Tuple[Dimension, List[Any]]:
            try:
                docs = await self.retriever.retrieve(
                    query=DIMENSION_QUERIES[dim],
                    k=top_k,
                    filter_metadata=filter_meta,
                    use_hyde=False,
                )
                return dim, docs
            except Exception as exc:
                logger.warning(
                    "dimension_retrieval_failed",
                    dimension=dim.value,
                    error=str(exc),
                )
                return dim, []

        results = await asyncio.gather(*[_retrieve_one(d) for d in ALL_DIMENSIONS])
        return dict(results)

    async def _generate_all_justifications(
        self,
        ticker: str,
        dimension_scores: Dict[Dimension, DimensionScore],
        evidence_map: Dict[Dimension, List[Any]],
    ) -> Dict[Dimension, ScoreJustification]:
        """
        Generate per-dimension justifications concurrently.
        """

        async def _justify_one(
            dim: Dimension,
        ) -> Tuple[Dimension, ScoreJustification]:
            score = dimension_scores[dim].score
            evidence = evidence_map.get(dim, [])
            justification = await self.justification_generator.generate(
                company_id=ticker,
                dimension=dim,
                score=score,
                evidence=evidence,
            )
            return dim, justification

        results = await asyncio.gather(*[_justify_one(d) for d in ALL_DIMENSIONS])
        return dict(results)

    def _build_assessment(
        self,
        ticker: str,
        dimension_scores: Dict[Dimension, DimensionScore],
        company: Company,
    ) -> CompanyAssessment:
        """
        Compute V^R, H^R, Synergy and OrgAIR scores from dimension scores.

        Uses a simplified weighted-average approach that mirrors the CS3
        ``DIMENSION_WEIGHTS`` without importing the full scoring engine,
        keeping this workflow self-contained.
        """
        # Dimension weights (matches app/models/dimension.py DIMENSION_WEIGHTS)
        weights = {
            Dimension.DATA_INFRASTRUCTURE: 0.25,
            Dimension.AI_GOVERNANCE: 0.20,
            Dimension.TECHNOLOGY_STACK: 0.15,
            Dimension.TALENT: 0.15,
            Dimension.LEADERSHIP: 0.10,
            Dimension.USE_CASE_PORTFOLIO: 0.10,
            Dimension.CULTURE: 0.05,
        }

        vr_score = sum(
            dimension_scores[d].score * w for d, w in weights.items()
            if d in dimension_scores
        )

        # H^R: simplified market position adjustment (0.8 – 1.2 multiplier)
        position_factor = min(1.0 + (company.market_cap_percentile - 0.5) * 0.4, 1.2)
        position_factor = max(position_factor, 0.8)
        hr_score = min(vr_score * position_factor, 100.0)

        # Synergy: geometric blend
        synergy_score = (vr_score * hr_score) ** 0.5

        # OrgAIR composite
        org_air_score = 0.6 * vr_score + 0.4 * synergy_score

        talent_score = dimension_scores.get(Dimension.TALENT)
        talent_concentration = talent_score.score / 100.0 if talent_score else 0.0

        evidence_counts = [ds.evidence_count for ds in dimension_scores.values()]
        total_evidence = sum(evidence_counts)
        ci = approximate_confidence_interval(org_air_score, total_evidence)

        return CompanyAssessment(
            company_id=ticker,
            assessment_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            vr_score=round(vr_score, 2),
            hr_score=round(hr_score, 2),
            synergy_score=round(synergy_score, 2),
            org_air_score=round(org_air_score, 2),
            confidence_interval=ci,
            dimension_scores=dimension_scores,
            talent_concentration=round(talent_concentration, 4),
            position_factor=round(position_factor, 4),
        )

    async def _synthesise_executive_memo(
        self,
        ticker: str,
        company: Company,
        assessment: CompanyAssessment,
        justifications: Dict[Dimension, ScoreJustification],
    ) -> Dict[str, Any]:
        """
        Call the LLM to produce the executive summary, key strengths / gaps,
        risk factors, and recommendation.  Falls back to structured defaults
        if the LLM call fails.
        """
        # Build a compact dimension digest for the prompt
        dim_digest = "\n".join(
            f"  • {dim.value.replace('_', ' ').title()}: "
            f"{j.score:.1f}/100 ({j.level_name}) — {j.generated_summary[:200]}"
            for dim, j in justifications.items()
        )

        system_prompt = (
            "You are a Managing Director at a leading Private Equity firm. "
            "You are preparing a concise IC Meeting Package for a deal committee. "
            "Respond with a JSON object containing these exact keys: "
            "executive_summary (3-4 sentences), "
            "key_strengths (list of 3 strings), "
            "key_gaps (list of 3 strings), "
            "risk_factors (list of 3 strings), "
            "recommendation (1 sentence: Buy / Hold / Pass with rationale)."
        )

        user_prompt = (
            f"Company: {company.name} ({ticker})\n"
            f"Sector: {company.sector.value}\n"
            f"OrgAIR Score: {assessment.org_air_score:.1f}/100\n"
            f"V^R: {assessment.vr_score:.1f}  H^R: {assessment.hr_score:.1f}  "
            f"Synergy: {assessment.synergy_score:.1f}\n\n"
            f"Dimension Summary:\n{dim_digest}\n\n"
            "Produce the IC Meeting Package JSON now."
        )

        try:
            response = await self.llm_router.complete(
                task=TaskType.JUSTIFICATION_GENERATION,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            import json
            parsed = json.loads(raw)

            return {
                "executive_summary": str(parsed.get("executive_summary", "")),
                "key_strengths": list(parsed.get("key_strengths", [])),
                "key_gaps": list(parsed.get("key_gaps", [])),
                "risk_factors": list(parsed.get("risk_factors", [])),
                "recommendation": str(parsed.get("recommendation", "")),
            }

        except Exception as exc:
            logger.error(
                "executive_memo_synthesis_failed",
                ticker=ticker,
                error=str(exc),
            )
            # Graceful fallback: derive from dimension scores
            top_dims = sorted(
                justifications.items(), key=lambda x: x[1].score, reverse=True
            )
            strengths = [
                f"{d.value.replace('_', ' ').title()} ({j.score:.0f}/100)"
                for d, j in top_dims[:3]
            ]
            gaps = [
                f"{d.value.replace('_', ' ').title()} ({j.score:.0f}/100)"
                for d, j in top_dims[-3:]
            ]

            return {
                "executive_summary": (
                    f"{company.name} ({ticker}) achieved an OrgAIR score of "
                    f"{assessment.org_air_score:.1f}/100, indicating "
                    f"{'above-average' if assessment.org_air_score >= 60 else 'below-average'} "
                    "AI maturity for its sector. "
                    "Detailed dimension analysis and supporting evidence are included below."
                ),
                "key_strengths": strengths,
                "key_gaps": gaps,
                "risk_factors": [
                    "Evidence base may be incomplete — run /ingest to refresh.",
                    "LLM synthesis unavailable; manual review recommended.",
                    "Score confidence intervals are wide with limited evidence.",
                ],
                "recommendation": (
                    "Hold — further diligence required to validate AI maturity claims."
                ),
            }
