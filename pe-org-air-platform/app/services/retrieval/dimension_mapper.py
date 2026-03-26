"""
Evidence-to-Dimension Mapper.

Codifies the Signal-to-Dimension mapping matrix so that
every piece of evidence retrieved by the RAG engine is tagged with the
correct OrgAIR scoring dimension (e.g. a "Job Post" for an AI role
should justify the "TALENT" dimension, not "TECHNOLOGY_STACK").

This module is already referenced in ``vector_store.py`` line 68 via
``dimension_mapper.get_primary_dimension()`` — creating this file
closes that open gap.
"""

from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.models.enums import Dimension
from app.models.rag import SignalCategory, SourceType

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Mapping matrix
# ---------------------------------------------------------------------------
# (signal_category) → (primary_dimension, confidence_boost)
#
# The boost is a small additive float applied when the evidence clearly
# fits the dimension, giving the scoring engine higher certainty.

_SIGNAL_TO_DIMENSION: Dict[str, Tuple[Dimension, float]] = {
    # -- CS2 external signal categories ------------------------------------
    SignalCategory.TECHNOLOGY_HIRING.value: (Dimension.TALENT, 0.10),
    SignalCategory.TALENT.value:            (Dimension.TALENT, 0.10),
    SignalCategory.INNOVATION_ACTIVITY.value:(Dimension.USE_CASE_PORTFOLIO, 0.05),
    SignalCategory.INNOVATION.value:        (Dimension.USE_CASE_PORTFOLIO, 0.05),
    SignalCategory.DIGITAL_PRESENCE.value:  (Dimension.TECHNOLOGY_STACK, 0.05),
    SignalCategory.TECHNOLOGY_STACK.value:   (Dimension.TECHNOLOGY_STACK, 0.05),
    SignalCategory.LEADERSHIP_SIGNALS.value: (Dimension.LEADERSHIP, 0.10),
    SignalCategory.LEADERSHIP.value:        (Dimension.LEADERSHIP, 0.10),
    SignalCategory.CULTURE_SIGNALS.value:   (Dimension.CULTURE, 0.05),
    SignalCategory.GOVERNANCE_SIGNALS.value: (Dimension.AI_GOVERNANCE, 0.10),
    # -- SEC filing categories ---------------------------------------------
    SignalCategory.SEC_FILING.value:        (Dimension.DATA_INFRASTRUCTURE, 0.05),
    # -- Catch-all ----------------------------------------------------------
    SignalCategory.GENERAL.value:           (Dimension.DATA_INFRASTRUCTURE, 0.0),
}

# Source-type overrides: when a specific *source* type is more descriptive
# than the category (e.g. a patent from USPTO should map to innovation no
# matter what category label it carries).
_SOURCE_OVERRIDES: Dict[str, Tuple[Dimension, float]] = {
    SourceType.PATENT.value:             (Dimension.USE_CASE_PORTFOLIO, 0.05),
    SourceType.PATENT_USPTO.value:       (Dimension.USE_CASE_PORTFOLIO, 0.05),
    SourceType.JOB_POSTING.value:        (Dimension.TALENT, 0.10),
    SourceType.JOB_POSTING_LINKEDIN.value:(Dimension.TALENT, 0.10),
    SourceType.JOB_POSTING_INDEED.value: (Dimension.TALENT, 0.10),
    SourceType.GLASSDOOR.value:          (Dimension.CULTURE, 0.05),
    SourceType.GLASSDOOR_REVIEW.value:   (Dimension.CULTURE, 0.05),
    SourceType.BOARD_PROXY_DEF14A.value: (Dimension.AI_GOVERNANCE, 0.10),
    SourceType.ANALYST_INTERVIEW.value:  (Dimension.LEADERSHIP, 0.05),
    SourceType.DD_DATA_ROOM.value:       (Dimension.DATA_INFRASTRUCTURE, 0.05),
    SourceType.DD_FINDING.value:         (Dimension.DATA_INFRASTRUCTURE, 0.05),
}


class DimensionMapper:
    """
    Maps signal categories and source types to OrgAIR scoring dimensions.

    Usage::

        mapper = DimensionMapper()
        dim = mapper.get_primary_dimension(SignalCategory.TECHNOLOGY_HIRING)
        # → Dimension.TALENT
    """

    # -- public API ---------------------------------------------------------

    def get_primary_dimension(
        self,
        signal_category: Any,
        source_type: Optional[Any] = None,
    ) -> Dimension:
        """
        Resolve the primary scoring dimension.

        Priority order:
        1. Source-type override  (most specific)
        2. Signal-category map  (general)
        3. Fallback to ``DATA_INFRASTRUCTURE``
        """
        # Normalise to string values
        cat_val = signal_category.value if hasattr(signal_category, "value") else str(signal_category)
        src_val = source_type.value if hasattr(source_type, "value") else str(source_type) if source_type else None

        # 1. Try source override first
        if src_val and src_val in _SOURCE_OVERRIDES:
            dim, _ = _SOURCE_OVERRIDES[src_val]
            return dim

        # 2. Category map
        if cat_val in _SIGNAL_TO_DIMENSION:
            dim, _ = _SIGNAL_TO_DIMENSION[cat_val]
            return dim

        # 3. Fallback
        logger.warning("dimension_mapper_fallback", signal_category=cat_val, source_type=src_val)
        return Dimension.DATA_INFRASTRUCTURE

    def get_confidence_boost(
        self,
        signal_category: Any,
        source_type: Optional[Any] = None,
    ) -> float:
        """Return the additive confidence boost for a given signal/source pair."""
        cat_val = signal_category.value if hasattr(signal_category, "value") else str(signal_category)
        src_val = source_type.value if hasattr(source_type, "value") else str(source_type) if source_type else None

        if src_val and src_val in _SOURCE_OVERRIDES:
            _, boost = _SOURCE_OVERRIDES[src_val]
            return boost

        if cat_val in _SIGNAL_TO_DIMENSION:
            _, boost = _SIGNAL_TO_DIMENSION[cat_val]
            return boost

        return 0.0

    def get_all_mappings(self) -> List[Dict[str, Any]]:
        """
        Return the full mapping matrix as a list of dicts.

        Useful for the frontend settings / transparency page.
        """
        rows: List[Dict[str, Any]] = []
        for cat, (dim, boost) in _SIGNAL_TO_DIMENSION.items():
            rows.append({
                "signal_category": cat,
                "primary_dimension": dim.value,
                "confidence_boost": boost,
                "mapping_source": "category",
            })
        for src, (dim, boost) in _SOURCE_OVERRIDES.items():
            rows.append({
                "source_type": src,
                "primary_dimension": dim.value,
                "confidence_boost": boost,
                "mapping_source": "source_override",
            })
        return rows
