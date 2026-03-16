
import asyncio
import structlog
import logging
import uuid
import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional

from app.services.snowflake import db
from app.services.redis_cache import cache
from app.scoring.rubric_scorer import RubricScorer
from app.pipelines.board_analyzer import BoardCompositionAnalyzer
from app.scoring.talent_analyzer import TalentConcentrationCalculator
from app.pipelines.glassdoor.glassdoor_collector import GlassdoorCultureCollector
from app.scoring.calculators import OrgAIRCalculator
from app.models.signals import SignalCategory
from app.models.scoring import SignalSource
from app.services.sector_config import sector_config
from app.scoring.position_factor import PositionFactorCalculator


logger = structlog.get_logger(__name__)

class IntegrationPipeline:
    """
    Case Study 3 Integration Pipeline.
    Refactored for Airflow DAG usage with granular methods.
    """

    def __init__(self):
        self.rubric_scorer = RubricScorer()
        self.board_analyzer = BoardCompositionAnalyzer()
        self.talent_calculator = TalentConcentrationCalculator()
        self.culture_collector = GlassdoorCultureCollector()
        self.org_air_calc = OrgAIRCalculator()
        self.pf_calculator = PositionFactorCalculator()

    async def get_active_tickers(self) -> List[str]:
        """Fetch all tickers that should be processed."""
        companies = await db.fetch_all_companies()
        return [c['ticker'] for c in companies]

    async def init_company_assessment(self, ticker: str) -> Dict[str, Any]:
        """
        Step 1: Initialize assessment record and fetch base signals.
        Returns context dict for subsequent tasks.
        """
        logger.info(f"Initializing assessment for {ticker}")
        
        company = await db.fetch_company_by_ticker(ticker)
        if not company:
            raise ValueError(f"Company {ticker} not found")
        
        company_id = company['id']
        
        # specific logic to get base scores from existing signals
        summary = await db.fetch_company_signal_summary(company_id)
        
        # Base dimensions from signals
        base_scores = {
            "data_infrastructure": Decimal(str(summary.get('digital_presence_score', 50.0) if summary else 50.0)),
            "technology_stack": Decimal(str(summary.get('technology_hiring_score', 50.0) if summary else 50.0)),
            "talent": Decimal(str(summary.get('technology_hiring_score', 50.0) if summary else 50.0)),
            "leadership": Decimal(str(summary.get('leadership_signals_score', 50.0) if summary else 50.0)),
            "culture": Decimal(str(summary.get('innovation_activity_score', 50.0) if summary else 50.0))
        }

        # Create a temporary assessment ID (or use a stable one for the day)
        assessment_id = str(uuid.uuid4())
        
        # Persist base state to DB (e.g., creating a draft assessment)
        # For now, we'll return this context to be passed to next tasks via XCom
        # Fetch industry to get correct HR base
        industry = None
        if company.get('industry_id'):
            # Fetch industry data based on company's industry_id
            query = "SELECT * FROM industries WHERE id = %s"
            ind_record = await db.fetch_one(query, (company['industry_id'],))
            if ind_record:
                industry = ind_record

        hr_base = float(industry.get('h_r_base', 70.0)) if industry else 70.0
        sector = industry.get('sector', 'default') if industry else company.get('sector', 'default')

        return {
            "ticker": ticker,
            "company_id": company_id,
            "assessment_id": assessment_id,
            "base_scores": {k: float(v) for k, v in base_scores.items()},
            "sector": sector,
            "hr_base": hr_base,
            "position_factor": float(company.get('position_factor', 0.5)),
            "market_cap_percentile": float(company.get('market_cap_percentile', 0.5))
        }

    async def analyze_sec_rubric(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Step 2: Run SEC Rubric Analysis.
        """
        company_id = context['company_id']
        logger.info(f"Running SEC Rubric Analysis for {context['ticker']}")
        
        chunks = await db.fetch_sec_chunks_by_company(company_id, limit=2000)
        if not chunks:
            logger.warning(f"No SEC chunks found for {context['ticker']}")
            return {}

        full_text = "\n".join([c['chunk_text'] for c in chunks if c.get('chunk_text')])
        
        results = {}
        tasks = [
            ("use_case_portfolio", SignalSource.SEC_ITEM_1),
            ("ai_governance", SignalSource.SEC_ITEM_1A),
            ("leadership", SignalSource.SEC_ITEM_7)
        ]
        
        for dim, source in tasks:
            res = self.rubric_scorer.score_dimension(dim, full_text, {})
            if float(res.score) > 10:
                await self._save_signal(company_id, source.value, "SEC Analytical Rubric", res.score, res.confidence, res.rationale, {
                    "matched_keywords": res.matched_keywords,
                    "level": res.level.name
                })
                results[dim] = float(res.score)
                
        return results

    async def analyze_board(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Step 3: Run Board Composition Analysis.
        """
        ticker = context['ticker']
        company_id = context['company_id']
        logger.info(f"Running Board Analysis for {ticker}")
        
        try:
            members, committees = self.board_analyzer.fetch_board_data(ticker)
            if members:
                # We need strategy text from SEC 10-K Item 1 usually
                # For now, we'll fetch a snippet if possible or pass empty
                chunks = await db.fetch_sec_chunks_by_company(company_id, limit=50) 
                strategy_text = " ".join([c['chunk_text'] for c in chunks[:5]]) if chunks else ""
                
                gov_signal = self.board_analyzer.analyze_board(company_id, ticker, members, committees, strategy_text)
                await self._save_signal(company_id, SignalCategory.BOARD_COMPOSITION, "Board Audit", gov_signal.governance_score, gov_signal.confidence, "Board composition analysis.", {
                    "ai_experts": gov_signal.ai_experts,
                    "committees": gov_signal.relevant_committees,
                    "independent_ratio": float(gov_signal.independent_ratio)
                })
                return {"ai_governance": float(gov_signal.governance_score)}
        except Exception as e:
            logger.error(f"Board analysis failed for {ticker}: {e}")
            
        return {}

    async def analyze_talent(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Step 4: Run Talent Concentration Analysis.
        Returns dict with HR modifier or scores.
        """
        company_id = context['company_id']
        logger.info(f"Running Talent Analysis for {context['ticker']}")
        
        try:
            talent_risk = await self.talent_calculator.get_company_talent_risk(company_id, db)
            tc_score = Decimal(str(talent_risk["talent_concentration_score"]))
            
            await self._save_signal(
                company_id, SignalCategory.TALENT_CONCENTRATION, "Talent Scorer", 
                tc_score * 100, Decimal("0.85"), 
                "Talent concentration risk assessment.", talent_risk["breakdown"]
            )
            
            return {
                "hr_modifier": float(talent_risk["talent_risk_adjustment"])
            }
        except Exception as e:
            logger.error(f"Talent analysis failed for {context['ticker']}: {e}")
            return {"hr_modifier": 1.0}

    async def analyze_culture(self, context: Dict[str, Any]) -> Dict[str, float]:
        """
        Step 5: Run Glassdoor Culture Analysis.
        """
        company_id = context['company_id']
        ticker = context['ticker']
        logger.info(f"Running Cultural Analysis for {ticker}")
        
        try:
            raw_reviews_data = await db.fetch_glassdoor_reviews_for_talent(company_id)
            if raw_reviews_data:
                from app.models.glassdoor_models import GlassdoorReview
                parsed_reviews = []
                for r in raw_reviews_data:
                    meta = r.get('metadata')
                    if isinstance(meta, str) and meta: meta = json.loads(meta)
                    parsed_reviews.append(GlassdoorReview(
                        id=str(uuid.uuid4()), company_id=company_id, ticker=ticker,
                        review_date=datetime.now(), rating=0.0,
                        title=r['title'], pros=r['review_text'], cons="",
                        is_current_employee=True, raw_json={}
                    ))
                
                culture_signal = self.culture_collector.analyze_reviews(company_id, ticker, parsed_reviews)
                if culture_signal:
                    await self._save_signal(
                        company_id, SignalCategory.GLASSDOOR_REVIEWS, "Glassdoor Cultural Audit",
                        culture_signal.overall_sentiment, culture_signal.confidence,
                        "Cultural alignment and AI awareness among employees.",
                        {"innovation": float(culture_signal.innovation_score), "ai_awareness": float(culture_signal.ai_awareness_score)}
                    )
                    return {"culture": float(culture_signal.overall_sentiment)}
        except Exception as e:
            logger.error(f"Culture analysis failed for {ticker}: {e}")
            
        return {}

    async def calculate_final_score(self, context: Dict[str, Any], sec_results: Dict, board_results: Dict, talent_results: Dict, culture_results: Dict) -> Dict[str, Any]:
        """
        Step 6: Aggregate all results and calculate final Org-AI-R score.
        """
        ticker = context['ticker']
        company_id = context['company_id']
        assessment_id = context['assessment_id']
        logger.info(f"Calculating Final Score for {ticker}")
        
        # Merge all Dimension Scores directly
        # Base scores from init
        scores = {k: Decimal(str(v)) for k, v in context['base_scores'].items()}
        
        # Merge SEC results
        for k, v in sec_results.items():
            if k in scores:
                scores[k] = (scores[k] * Decimal("0.3") + Decimal(str(v)) * Decimal("0.7"))
            else:
                scores[k] = Decimal(str(v))

        # Merge Board results
        if "ai_governance" in board_results:
            val = Decimal(str(board_results["ai_governance"]))
            if "ai_governance" in scores:
                scores["ai_governance"] = (scores["ai_governance"] * Decimal("0.6") + val * Decimal("0.4"))
            else:
                scores["ai_governance"] = val

        # Merge Culture results
        if "culture" in culture_results:
            val = Decimal(str(culture_results["culture"]))
            scores["culture"] = (scores["culture"] * Decimal("0.5") + val * Decimal("0.5"))

        # Dimensions List
        final_dimensions = ["data_infrastructure", "ai_governance", "technology_stack", "talent", "leadership", "use_case_portfolio", "culture"]
        dimension_inputs = {}
        for d in final_dimensions:
            dimension_inputs[d] = scores.get(d, Decimal("50.0"))

        hr_modifier = Decimal(str(talent_results.get("hr_modifier", 1.0)))
        base_hr_val = str(context.get("hr_base", 70.0))
        hr_base_adjusted = Decimal(base_hr_val) * hr_modifier

        # Calculate V^R score first to use in Position Factor
        sector = context.get('sector', 'default')
        vr_score = self.org_air_calc.vr_calc.calculate_vr(dimension_inputs, sector)

        # Calculate Dynamic Position Factor using Improved logic
        mcap_p = float(context.get('market_cap_percentile', 0.5))
        pf_decimal = self.pf_calculator.calculate_position_factor(
            float(vr_score),
            sector,
            mcap_p
        )
        position_factor = pf_decimal

        dimension_confidences = [Decimal("0.8")] * len(dimension_inputs)

        final_org_air = self.org_air_calc.calculate_org_air(
            dimension_scores=dimension_inputs,
            dimension_confidences=dimension_confidences,
            position_factor=position_factor,
            hr_base=hr_base_adjusted,
            sector=sector,
            company_id=company_id,
            alpha=Decimal("0.60"), # V^R vs H^R within 88%
            beta=Decimal("0.12")   # Synergy weight
        )

        # Persistence
        await db.create_assessment({
            "id": assessment_id, "company_id": company_id, 
            "assessment_type": "INTEGRATED_CS3", "assessment_date": date.today().isoformat(),
            "primary_assessor": "IntegrationPipeline", "status": "completed"
        })
        
        for dim, score in dimension_inputs.items():
            await db.create_dimension_score({
                "id": str(uuid.uuid4()), "assessment_id": assessment_id, "dimension": dim,
                "score": float(score), "weight": float(sector_config.get_weights(sector).get(dim, 0.14)),
                "confidence": 0.8, "evidence_count": 1
            })
            
        update_query = """
            UPDATE assessments 
            SET org_air_score = %s, 
                v_r_score = %s, 
                h_r_score = %s, 
                synergy_score = %s, 
                confidence_score = %s,
                confidence_lower = %s, 
                confidence_upper = %s 
            WHERE id = %s
        """
        await db.execute(update_query, (
            final_org_air["org_air_score"], 
            final_org_air["v_r"],
            final_org_air["h_r"],
            final_org_air["synergy"],
            final_org_air["confidence"],
            final_org_air["ci_lower"], 
            final_org_air["ci_upper"], 
            assessment_id
        ))

        return {
            "ticker": ticker,
            "final_score": final_org_air,
            "assessment_id": assessment_id,
            "company_id": company_id,
            "scores": dimension_inputs,
            "signals_added": 0
        }

    async def _save_signal(self, company_id: str, category: str, source: str, score: Decimal, confidence: Decimal, rationale: str, metadata: dict):
        hash_input = f"{company_id}{category}{score}"
        signal_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        signal = {
            "id": str(uuid.uuid4()),
            "company_id": company_id,
            "signal_hash": signal_hash,
            "category": category,
            "source": source,
            "signal_date": date.today().isoformat(),
            "raw_value": rationale[:500],
            "normalized_score": float(score),
            "confidence": float(confidence),
            "metadata": metadata
        }
        await db.create_external_signal(signal)

    # Legacy method wrapper for backward compatibility if needed
    async def run_integration(self, ticker: str) -> Dict[str, Any]:
        """Legacy wrapper for backward compatibility."""
        context = await self.init_company_assessment(ticker)
        sec_res = await self.analyze_sec_rubric(context)
        board_res = await self.analyze_board(context)
        talent_res = await self.analyze_talent(context)
        culture_res = await self.analyze_culture(context)
        return await self.calculate_final_score(context, sec_res, board_res, talent_res, culture_res)

integration_pipeline = IntegrationPipeline()
