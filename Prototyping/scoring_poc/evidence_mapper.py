from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from decimal import Decimal

class Dimension(str, Enum):
    DATA_INFRASTRUCTURE = "data_infrastructure"
    AI_GOVERNANCE = "ai_governance"
    TECHNOLOGY_STACK = "technology_stack"
    TALENT = "talent"
    LEADERSHIP = "leadership"
    USE_CASE_PORTFOLIO = "use_case_portfolio"
    CULTURE = "culture"

class SignalSource(str, Enum):
    # CS2 External Signals
    TECHNOLOGY_HIRING = "technology_hiring"
    INNOVATION_ACTIVITY = "innovation_activity"
    DIGITAL_PRESENCE = "digital_presence"
    LEADERSHIP_SIGNALS = "leadership_signals"
    # CS2 SEC Sections
    SEC_ITEM_1 = "sec_item_1"
    SEC_ITEM_1A = "sec_item_1a"
    SEC_ITEM_7 = "sec_item_7"
    # CS3 New Sources
    GLASSDOOR_REVIEWS = "glassdoor_reviews"
    BOARD_COMPOSITION = "board_composition"

@dataclass
class DimensionMapping:
    """Maps a signal source to dimensions with weights."""
    source: SignalSource
    primary_dimension: Dimension
    primary_weight: Decimal
    secondary_mappings: Dict[Dimension, Decimal] = field(default_factory=dict)
    reliability: Decimal = Decimal("0.8") # Source reliability

@dataclass
class EvidenceScore:
    """A score from a single evidence source."""
    source: SignalSource
    raw_score: Decimal      # 0-100
    confidence: Decimal     # 0-1
    evidence_count: int
    metadata: Dict = field(default_factory=dict)

@dataclass
class DimensionScore:
    """Aggregated score for one dimension."""
    dimension: Dimension
    score: Decimal
    contributing_sources: List[SignalSource]
    total_weight: Decimal
    confidence: Decimal

# THE CRITICAL MAPPING TABLE
# From Lab PDF Task 5.0a (Table 1 + Code Hints)
SIGNAL_TO_DIMENSION_MAP: Dict[SignalSource, DimensionMapping] = {

    # 1. TECHNOLOGY HIRING -> Talent(0.70), Tech(0.20), Culture(0.10)
    SignalSource.TECHNOLOGY_HIRING: DimensionMapping(
        source=SignalSource.TECHNOLOGY_HIRING,
        primary_dimension=Dimension.TALENT,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.20"),
            Dimension.CULTURE: Decimal("0.10"),
        },
        reliability=Decimal("0.85"),
    ),

    # 2. INNOVATION ACTIVITY -> Tech(0.50), Use Case(0.30), Data Infra(0.20)
    SignalSource.INNOVATION_ACTIVITY: DimensionMapping(
        source=SignalSource.INNOVATION_ACTIVITY,
        primary_dimension=Dimension.TECHNOLOGY_STACK,
        primary_weight=Decimal("0.50"),
        secondary_mappings={
            Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.80"),
    ),

    # 3. DIGITAL PRESENCE -> Data Infra(0.60), Tech(0.40)
    SignalSource.DIGITAL_PRESENCE: DimensionMapping(
        source=SignalSource.DIGITAL_PRESENCE,
        primary_dimension=Dimension.DATA_INFRASTRUCTURE,
        primary_weight=Decimal("0.60"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.40"),
        },
        reliability=Decimal("0.90"), # Usually robust web data
    ),

    # 4. LEADERSHIP SIGNALS -> Leadership(0.60), Gov(0.25), Culture(0.15)
    SignalSource.LEADERSHIP_SIGNALS: DimensionMapping(
        source=SignalSource.LEADERSHIP_SIGNALS,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("0.60"),
        secondary_mappings={
            Dimension.AI_GOVERNANCE: Decimal("0.25"),
            Dimension.CULTURE: Decimal("0.15"),
        },
        reliability=Decimal("0.75"), # Often sparse
    ),

    # 5. SEC ITEM 1 (Business) -> Use Case(0.70), Tech(0.30)
    SignalSource.SEC_ITEM_1: DimensionMapping(
        source=SignalSource.SEC_ITEM_1,
        primary_dimension=Dimension.USE_CASE_PORTFOLIO,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.TECHNOLOGY_STACK: Decimal("0.30"),
        },
        reliability=Decimal("0.95"), # Filed regulatory docs
    ),

    # 6. SEC ITEM 1A (Risk) -> Gov(0.80), Data(0.20)
    SignalSource.SEC_ITEM_1A: DimensionMapping(
        source=SignalSource.SEC_ITEM_1A,
        primary_dimension=Dimension.AI_GOVERNANCE,
        primary_weight=Decimal("0.80"),
        secondary_mappings={
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.95"),
    ),

    # 7. SEC ITEM 7 (MD&A) -> Leadership(0.50), Use Case(0.30), Data(0.20)
    SignalSource.SEC_ITEM_7: DimensionMapping(
        source=SignalSource.SEC_ITEM_7,
        primary_dimension=Dimension.LEADERSHIP,
        primary_weight=Decimal("0.50"),
        secondary_mappings={
            Dimension.USE_CASE_PORTFOLIO: Decimal("0.30"),
            Dimension.DATA_INFRASTRUCTURE: Decimal("0.20"),
        },
        reliability=Decimal("0.90"),
    ),

    # 8. GLASSDOOR REVIEWS -> Culture(0.80), Talent(0.10), Leadership(0.10)
    SignalSource.GLASSDOOR_REVIEWS: DimensionMapping(
        source=SignalSource.GLASSDOOR_REVIEWS,
        primary_dimension=Dimension.CULTURE,
        primary_weight=Decimal("0.80"),
        secondary_mappings={
            Dimension.TALENT: Decimal("0.10"),
            Dimension.LEADERSHIP: Decimal("0.10"),
        },
        reliability=Decimal("0.60"), # Subjective, prone to bias
    ),

    # 9. BOARD COMPOSITION -> Gov(0.70), Leadership(0.30)
    SignalSource.BOARD_COMPOSITION: DimensionMapping(
        source=SignalSource.BOARD_COMPOSITION,
        primary_dimension=Dimension.AI_GOVERNANCE,
        primary_weight=Decimal("0.70"),
        secondary_mappings={
            Dimension.LEADERSHIP: Decimal("0.30"),
        },
        reliability=Decimal("0.90"), # Formal structured data
    )
}

class EvidenceMapper:
    """Maps CS2 evidence to 7 V^R dimensions."""

    def __init__(self):
        self.mappings = SIGNAL_TO_DIMENSION_MAP

    def map_evidence_to_dimensions(
        self,
        evidence_scores: List[EvidenceScore],
    ) -> Dict[Dimension, DimensionScore]:
        """
        Convert CS2 evidence scores to 7 dimension scores.
        """
        
        # Initialize accumulators for each dimension
        dimension_sums: Dict[Dimension, Decimal] = {d: Decimal(0) for d in Dimension}
        dimension_weights: Dict[Dimension, Decimal] = {d: Decimal(0) for d in Dimension}
        dimension_sources: Dict[Dimension, List[SignalSource]] = {d: [] for d in Dimension}

        # Process each evidence score
        for ev in evidence_scores:
            mapping = self.mappings.get(ev.source)
            if not mapping:
                continue

            # Weight by confidence and reliability
            # Effective Score = Raw * Confidence * Reliability
            # But mathematically for weighted avg, we usually do: Sum(Score * Weight) / Sum(Weight)
            # Here, the PDF implies effective_score is the value to accumulate?
            # Let's use standard weighted average:
            # Value = ev.raw_score
            # Weight = contribution_weight * ev.confidence * mapping.reliability
            
            # 1. Primary Contribution
            dim = mapping.primary_dimension
            weight = mapping.primary_weight
            
            w = weight * ev.confidence * mapping.reliability
            dimension_sums[dim] += ev.raw_score * w
            dimension_weights[dim] += w
            if ev.source not in dimension_sources[dim]:
                dimension_sources[dim].append(ev.source)

            # 2. Secondary Contributions
            for sec_dim, sec_weight in mapping.secondary_mappings.items():
                w = sec_weight * ev.confidence * mapping.reliability
                dimension_sums[sec_dim] += ev.raw_score * w
                dimension_weights[sec_dim] += w
                if ev.source not in dimension_sources[sec_dim]:
                    dimension_sources[sec_dim].append(ev.source)

        # Calculate final scores
        results = {}
        for dim in Dimension:
            total_w = dimension_weights[dim]
            
            if total_w > 0:
                final_score = dimension_sums[dim] / total_w
                # Normalize confidence? Just taking avg confidence isn't perfect, 
                # but let's approximate by the total weight accumulation relative to distinct sources?
                # For now, let's just map the weighted score.
                
                # Confidence implies "how much signal did we actually get vs potential max?"
                # Simplified: min(1.0, total_weight / 2.0)? Let's just store total_weight as confidence proxy for now.
                # PDF says "confidence: Decimal" in DimensionScore.
                # Use total_weight as a raw confidence metric.
                conf = min(Decimal("1.0"), total_w) 
                
                results[dim] = DimensionScore(
                    dimension=dim,
                    score=round(final_score, 2),
                    contributing_sources=dimension_sources[dim],
                    total_weight=round(total_w, 2),
                    confidence=round(conf, 2)
                )
            else:
                # Default to 50.0 if no evidence
                results[dim] = DimensionScore(
                    dimension=dim,
                    score=Decimal("50.0"),
                    contributing_sources=[],
                    total_weight=Decimal("0.0"),
                    confidence=Decimal("0.0")
                )

        return results

    def get_coverage_report(self, evidence_scores: List[EvidenceScore]) -> Dict[Dimension, Dict]:
        """
        Report which dimensions have evidence and which have gaps.
        """
        mapped_scores = self.map_evidence_to_dimensions(evidence_scores)
        report = {}
        
        for dim, ds in mapped_scores.items():
            report[dim] = {
                "has_evidence": len(ds.contributing_sources) > 0,
                "source_count": len(ds.contributing_sources),
                "total_weight": float(ds.total_weight),
                "confidence": float(ds.confidence)
            }
        return report
