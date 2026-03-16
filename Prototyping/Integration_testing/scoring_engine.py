from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
import math
import re
import uuid
import datetime

# --- ENUMS & MODELS ---

class Dimension(str, Enum):
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"

class SignalSource(str, Enum):
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    SEC_ITEM_1 = "sec_item_1"
    SEC_ITEM_1A = "sec_item_1a"
    SEC_ITEM_7 = "sec_item_7"
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"

class ScoreLevel(Enum):
    LEVEL_5 = (80, 100, "Excellent")
    LEVEL_4 = (60, 79, "Good")
    LEVEL_3 = (40, 59, "Adequate")
    LEVEL_2 = (20, 39, "Developing")
    LEVEL_1 = (0, 19, "Nascent")

    @property
    def min_score(self) -> int:
        return self.value[0]

    @property
    def max_score(self) -> int:
        return self.value[1]

@dataclass
class DimensionMapping:
    source: SignalSource
    primary_dimension: Dimension
    primary_weight: Decimal
    secondary_mappings: Dict[Dimension, Decimal] = field(default_factory=dict)
    reliability: Decimal = Decimal("0.8")

@dataclass
class EvidenceScore:
    source: SignalSource
    raw_score: Decimal
    confidence: Decimal
    evidence_count: int
    metadata: Dict = field(default_factory=dict)

@dataclass
class DimensionScore:
    dimension: Dimension
    score: Decimal
    contributing_sources: List[SignalSource]
    total_weight: Decimal
    confidence: Decimal

@dataclass
class RubricCriteria:
    level: ScoreLevel
    keywords: List[str]
    min_keyword_matches: int

@dataclass
class RubricResult:
    dimension: str
    level: ScoreLevel
    score: Decimal
    matched_keywords: List[str]
    rationale: str

@dataclass
class JobAnalysis:
    total_ai_jobs: int
    senior_ai_jobs: int
    mid_ai_jobs: int
    entry_ai_jobs: int
    unique_skills: Set[str]
    raw_job_text: str = ""

@dataclass
class BoardMember:
    name: str
    title: str
    bio: str
    is_independent: bool
    tenure_years: int
    committees: List[str]

# --- UTILS ---

def to_decimal(value: float, places: int = 4) -> Decimal:
    return Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)

def clamp(value: Decimal, min_val: Decimal = Decimal(0), max_val: Decimal = Decimal(100)) -> Decimal:
    return max(min_val, min(max_val, value))

def weighted_mean(values: List[Decimal], weights: List[Decimal]) -> Decimal:
    if len(values) != len(weights): raise ValueError("Mismatch")
    if not values: return Decimal("0")
    total_w = sum(weights)
    if total_w == 0: return Decimal("0")
    return sum(v * w for v, w in zip(values, weights)) / total_w

# --- RUBRICS ---

DIMENSION_RUBRICS = {
    Dimension.USE_CASE_PORTFOLIO: {
        ScoreLevel.LEVEL_5: RubricCriteria(ScoreLevel.LEVEL_5, ["ai-first products", "enterprise scale", "generative ai production", "proprietary models"], 2),
        ScoreLevel.LEVEL_4: RubricCriteria(ScoreLevel.LEVEL_4, ["production ai", "operationalized", "automated workflows"], 2),
        ScoreLevel.LEVEL_3: RubricCriteria(ScoreLevel.LEVEL_3, ["pilot projects", "poc", "exploration"], 1),
    },
    Dimension.AI_GOVERNANCE: {
        ScoreLevel.LEVEL_5: RubricCriteria(ScoreLevel.LEVEL_5, ["caio", "chief ai officer", "board committee for technology", "algorithmic auditing"], 2),
        ScoreLevel.LEVEL_4: RubricCriteria(ScoreLevel.LEVEL_4, ["ai policy", "risk framework", "responsible ai"], 2),
        ScoreLevel.LEVEL_3: RubricCriteria(ScoreLevel.LEVEL_3, ["it governance", "data privacy"], 1),
    },
    Dimension.LEADERSHIP: {
        ScoreLevel.LEVEL_5: RubricCriteria(ScoreLevel.LEVEL_5, ["ceo mentioned ai", "strategic pillar", "ai first transformation"], 2),
        ScoreLevel.LEVEL_4: RubricCriteria(ScoreLevel.LEVEL_4, ["cto led ai", "digital transformation", "innovation hub"], 2),
    }
}

class RubricScorer:
    def score_text(self, text: str, dimension: Dimension) -> Decimal:
        text = text.lower()
        rubric = DIMENSION_RUBRICS.get(dimension, {})
        for level in [ScoreLevel.LEVEL_5, ScoreLevel.LEVEL_4, ScoreLevel.LEVEL_3]:
            crit = rubric.get(level)
            if not crit: continue
            matches = [kw for kw in crit.keywords if kw in text]
            if len(matches) >= crit.min_keyword_matches:
                density = len(matches) / len(crit.keywords)
                score = level.min_score + (density * (level.max_score - level.min_score))
                return Decimal(str(round(score, 2)))
        return Decimal("50.0")

# --- ANALYZERS ---

class DigitalPresenceAnalyzer:
    TECH_INDICATORS = {
        "cloud_ml": ["aws sagemaker", "azure ml", "google vertex", "databricks", "sagemaker", "vertex ai"],
        "ml_framework": ["tensorflow", "pytorch", "scikit-learn", "keras", "cuda", "onnx"],
        "data_platform": ["snowflake", "databricks", "spark", "hadoop", "bigquery", "redshift"],
        "ai_api": ["openai", "anthropic", "huggingface", "cohere", "langchain"]
    }

    def analyze(self, job_text: str) -> Decimal:
        text = job_text.lower()
        detections = []
        categories_found = set()
        for cat, techs in self.TECH_INDICATORS.items():
            for tech in techs:
                if tech in text:
                    detections.append(tech)
                    categories_found.add(cat)
        final_score = min(len(detections) * 10, 50) + min(len(categories_found) * 12.5, 50)
        return Decimal(str(round(final_score, 2)))

class BoardAnalyzer:
    TECH_PATTERNS = [r'\bai\b', r'\bartificial\s+intelligence\b', r'\bmachine\s+learning\b', r'\bchief\s+technology\b', r'\bcto\b', r'\bdigital\b']
    TECH_COMMITTEE_PATTERNS = [r'\btechnology\s+committee\b', r'\binnovation\s+committee\b', r'\bdigital\s+strategy\b']

    def analyze_board(self, members: List[BoardMember], committees: List[str]) -> Decimal:
        score = Decimal("20")
        if any(any(re.search(p, c.lower()) for p in self.TECH_COMMITTEE_PATTERNS) for c in committees):
            score += Decimal("15")
        if any(any(re.search(p, (m.bio + " " + m.title).lower()) for p in self.TECH_PATTERNS) for m in members):
            score += Decimal("20")
        if any("chief data" in m.title.lower() or "cdo" in m.title.lower() or "caio" in m.title.lower() for m in members):
            score += Decimal("15")
        if len(members) > 0:
            ratio = sum(1 for m in members if m.is_independent) / len(members)
            if ratio > 0.5: score += Decimal("10")
        return clamp(score, Decimal("20"), Decimal("100"))

# --- ENGINE ---

class ScoringIntegrationService:
    def __init__(self):
        self.rubric_scorer = RubricScorer()
        self.dp_analyzer = DigitalPresenceAnalyzer()
        self.board_analyzer = BoardAnalyzer()

    def score_company(self, ticker: str, sector: str, market_cap_p: float, evidence: List[EvidenceScore], job_analysis: JobAnalysis, board_members: List[BoardMember], board_committees: List[str], glassdoor_stats: Dict) -> Dict:
        # 1. Improved AI-Governance (Board) - Only add if not pre-calculated
        if not any(ev.source == SignalSource.BOARD_COMPOSITION for ev in evidence):
            if board_members or board_committees:
                board_score = self.board_analyzer.analyze_board(board_members, board_committees)
                evidence.append(EvidenceScore(SignalSource.BOARD_COMPOSITION, board_score, Decimal("0.95"), 1))
            else:
                # Default nascent if truly no data
                evidence.append(EvidenceScore(SignalSource.BOARD_COMPOSITION, Decimal("20.0"), Decimal("0.3"), 1))

        # 2. Improved Digital Presence (Fixing the 0.0 issue)
        dp_score = Decimal("0.0") # Initialize dp_score here
        for ev in evidence:
            if ev.source == SignalSource.DIGITAL_PRESENCE:
                dp_score = ev.raw_score
                break
        if dp_score == 0:
            dp_score = self.dp_analyzer.analyze(job_analysis.raw_job_text)
            evidence.append(EvidenceScore(SignalSource.DIGITAL_PRESENCE, dp_score, Decimal("0.85"), 1))

        sums = {d: Decimal(0) for d in Dimension}
        weights = {d: Decimal(0) for d in Dimension}
        for ev in evidence:
            m = SIGNAL_MAP.get(ev.source)
            if not m: continue
            w = m.primary_weight * ev.confidence * m.reliability
            sums[m.primary_dimension] += ev.raw_score * w
            weights[m.primary_dimension] += w
            for sd, sw in m.secondary_mappings.items():
                w = sw * ev.confidence * m.reliability
                sums[sd] += ev.raw_score * w
                weights[sd] += w
        
        dim_scores = {d: (sums[d]/weights[d] if weights[d] > 0 else Decimal("50.0")).quantize(Decimal("0.01")) for d in Dimension}

        leader_ratio = Decimal(job_analysis.senior_ai_jobs) / Decimal(max(1, job_analysis.total_ai_jobs))
        ts_factor = min(Decimal("1.0"), Decimal("1.0") / Decimal(str(math.sqrt(job_analysis.total_ai_jobs) + 0.1)))
        skill_conc = max(Decimal("0"), Decimal("1.0") - (Decimal(len(job_analysis.unique_skills)) / Decimal("15.0")))
        indiv_factor = min(Decimal("1.0"), Decimal(glassdoor_stats.get('mentions', 0)) / Decimal(max(1, glassdoor_stats.get('reviews', 1))))
        tc = Decimal("0.4")*leader_ratio + Decimal("0.3")*ts_factor + Decimal("0.2")*skill_conc + Decimal("0.1")*indiv_factor
        
        weights_vr = {Dimension.DATA_INFRASTRUCTURE: Decimal("0.15"), Dimension.AI_GOVERNANCE: Decimal("0.10"), Dimension.TECHNOLOGY_STACK: Decimal("0.20"), Dimension.TALENT: Decimal("0.20"), Dimension.LEADERSHIP: Decimal("0.10"), Dimension.USE_CASE_PORTFOLIO: Decimal("0.15"), Dimension.CULTURE: Decimal("0.10")}
        if sector == "financial_services": weights_vr.update({Dimension.AI_GOVERNANCE: Decimal("0.15"), Dimension.CULTURE: Decimal("0.05")})
        
        vr_score = clamp(sum(dim_scores[d] * weights_vr[d] for d in Dimension))
        pf = Decimal(str(round(0.6 * ((float(vr_score) - 50.0)/50.0) + 0.4 * ((market_cap_p - 0.5)*2), 2)))
        hr_score = clamp(Decimal("70.0") * (Decimal("1.0") - Decimal("0.15") * max(Decimal("0"), tc - Decimal("0.25"))) * (Decimal("1") + Decimal("0.15") * pf))
        synergy = (vr_score * hr_score) / Decimal("100")
        final = Decimal("0.6") * vr_score + Decimal("0.28") * hr_score + Decimal("0.12") * synergy
        
        return {
            "final_score": float(final), "vr_score": float(vr_score), "hr_score": float(hr_score),
            "synergy_score": float(synergy), "talent_concentration": float(tc), "position_factor": float(pf),
            "dimension_scores": {d.value: float(s) for d, s in dim_scores.items()}
        }

SIGNAL_MAP = {
    SignalSource.TECHNOLOGY_HIRING: DimensionMapping(SignalSource.TECHNOLOGY_HIRING, Dimension.TALENT, Decimal("0.70"), {Dimension.TECHNOLOGY_STACK: Decimal("0.20"), Dimension.CULTURE: Decimal("0.10"), Dimension.DATA_INFRASTRUCTURE: Decimal("0.10")}, Decimal("0.85")),
    SignalSource.INNOVATION_ACTIVITY: DimensionMapping(SignalSource.INNOVATION_ACTIVITY, Dimension.TECHNOLOGY_STACK, Decimal("0.50"), {Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"), Dimension.DATA_INFRASTRUCTURE: Decimal("0.20")}, Decimal("0.80")),
    SignalSource.DIGITAL_PRESENCE: DimensionMapping(SignalSource.DIGITAL_PRESENCE, Dimension.DATA_INFRASTRUCTURE, Decimal("0.60"), {Dimension.TECHNOLOGY_STACK: Decimal("0.40")}, Decimal("0.90")),
    SignalSource.LEADERSHIP_SIGNALS: DimensionMapping(SignalSource.LEADERSHIP_SIGNALS, Dimension.LEADERSHIP, Decimal("0.60"), {Dimension.AI_GOVERNANCE: Decimal("0.25"), Dimension.CULTURE: Decimal("0.15")}, Decimal("0.75")),
    SignalSource.SEC_ITEM_1: DimensionMapping(SignalSource.SEC_ITEM_1, Dimension.USE_CASE_PORTFOLIO, Decimal("0.70"), {Dimension.TECHNOLOGY_STACK: Decimal("0.30")}, Decimal("0.95")),
    SignalSource.SEC_ITEM_1A: DimensionMapping(SignalSource.SEC_ITEM_1A, Dimension.AI_GOVERNANCE, Decimal("0.80"), {Dimension.DATA_INFRASTRUCTURE: Decimal("0.20")}, Decimal("0.95")),
    SignalSource.SEC_ITEM_7: DimensionMapping(SignalSource.SEC_ITEM_7, Dimension.LEADERSHIP, Decimal("0.50"), {Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"), Dimension.DATA_INFRASTRUCTURE: Decimal("0.20")}, Decimal("0.90")),
    SignalSource.GLASSDOOR_REVIEWS: DimensionMapping(SignalSource.GLASSDOOR_REVIEWS, Dimension.CULTURE, Decimal("0.80"), {Dimension.TALENT: Decimal("0.10"), Dimension.LEADERSHIP: Decimal("0.10")}, Decimal("0.60")),
    SignalSource.BOARD_COMPOSITION: DimensionMapping(SignalSource.BOARD_COMPOSITION, Dimension.AI_GOVERNANCE, Decimal("0.70"), {Dimension.LEADERSHIP: Decimal("0.30")}, Decimal("0.90"))
}
