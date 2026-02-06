"""State definitions for LangGraph agent."""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from src.storage.models import AssetMove, MarketSnapshot, NewsArticle


class CandidateHypothesis(TypedDict):
    """A candidate narrative hypothesis to investigate."""

    hypothesis: str
    confidence: float  # 0-1
    supporting_factors: List[str]
    questions_to_investigate: List[str]
    priority: int  # Higher = more important


class InvestigationResult(TypedDict):
    """Result from investigating a hypothesis."""

    hypothesis: str
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    additional_context: List[str]
    confidence_adjustment: float  # How much to adjust confidence
    final_confidence: float


class AgentState(TypedDict):
    """State for the market narrative agent workflow.

    This state flows through 4 phases:
    1. Observation: Collect and analyze initial market data
    2. Hypothesis: Generate candidate explanations
    3. Investigation: Test hypotheses with targeted queries
    4. Synthesis: Create final narrative
    """

    # Phase tracking
    current_phase: str  # "observation", "hypothesis", "investigation", "synthesis"
    date: datetime

    # Phase 1: Observation outputs
    market_snapshot: Optional[MarketSnapshot]
    news_headlines: List[NewsArticle]
    significant_moves: List[AssetMove]
    initial_summary: str

    # Phase 2: Hypothesis outputs
    hypotheses: List[CandidateHypothesis]
    selected_hypotheses: List[str]  # IDs of hypotheses to investigate

    # Phase 3: Investigation outputs
    investigation_results: List[InvestigationResult]
    additional_data: Dict[str, Any]  # Flexible storage for tool outputs

    # Phase 4: Synthesis outputs
    primary_narrative: str
    supporting_narratives: List[str]
    key_moves_explained: Dict[str, str]  # symbol -> explanation
    unexplained_moves: List[str]
    prediction_insights: List[str]
    confidence_score: float
    looking_ahead: str

    # Metadata
    tools_used: List[str]
    errors: List[str]
    intermediate_outputs: List[Dict[str, Any]]


def create_initial_state(date: Optional[datetime] = None) -> AgentState:
    """Create initial agent state."""
    return AgentState(
        current_phase="observation",
        date=date or datetime.now(),
        market_snapshot=None,
        news_headlines=[],
        significant_moves=[],
        initial_summary="",
        hypotheses=[],
        selected_hypotheses=[],
        investigation_results=[],
        additional_data={},
        primary_narrative="",
        supporting_narratives=[],
        key_moves_explained={},
        unexplained_moves=[],
        prediction_insights=[],
        confidence_score=0.0,
        looking_ahead="",
        tools_used=[],
        errors=[],
        intermediate_outputs=[],
    )
