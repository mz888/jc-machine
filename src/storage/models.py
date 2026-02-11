"""Pydantic models for market data and narratives."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AssetMove(BaseModel):
    """Information about an asset's price movement."""

    symbol: str = Field(description="Asset ticker symbol")
    name: Optional[str] = Field(default=None, description="Asset name")
    price: float = Field(description="Current/closing price")
    change_percent: float = Field(description="Percent change")
    change_absolute: float = Field(description="Absolute price change")
    volume: Optional[float] = Field(default=None, description="Trading volume")
    volume_ratio: Optional[float] = Field(default=None, description="Volume vs average")


class MarketSnapshot(BaseModel):
    """Snapshot of market state at a point in time."""

    date: datetime = Field(description="Snapshot date")
    major_indices: Dict[str, float] = Field(description="Index returns (symbol: change%)")
    biggest_gainers: List[AssetMove] = Field(description="Top gaining assets")
    biggest_losers: List[AssetMove] = Field(description="Top losing assets")
    sector_performance: Dict[str, float] = Field(description="Sector returns")
    market_breadth: Optional[Dict[str, int]] = Field(
        default=None, description="Advancers/decliners/unchanged"
    )
    volatility: Optional[Dict[str, float]] = Field(default=None, description="VIX and other vol")


class NewsArticle(BaseModel):
    """A news article."""

    title: str = Field(description="Article title")
    url: Optional[str] = Field(default=None, description="Article URL")
    source: str = Field(description="News source")
    published_at: datetime = Field(description="Publication timestamp")
    summary: Optional[str] = Field(default=None, description="Article summary/description")
    keywords: List[str] = Field(default_factory=list, description="Relevant keywords")


class Prediction(BaseModel):
    """A prediction market question and probability."""

    question: str = Field(description="Prediction question")
    probability: float = Field(description="Current probability (0-1)")
    platform: str = Field(description="Prediction market platform")
    url: Optional[str] = Field(default=None, description="Link to prediction")
    last_updated: datetime = Field(description="When probability was last updated")
    volume: Optional[float] = Field(default=None, description="Trading volume if available")


class Evidence(BaseModel):
    """Evidence supporting or refuting a hypothesis."""

    type: str = Field(description="Evidence type: price, news, prediction, correlation")
    description: str = Field(description="What this evidence shows")
    source: str = Field(description="Where evidence came from")
    confidence: float = Field(description="Confidence in evidence (0-1)")


class CandidateNarrative(BaseModel):
    """A candidate narrative hypothesis."""

    hypothesis: str = Field(description="The narrative hypothesis")
    supporting_evidence: List[Evidence] = Field(description="Evidence supporting this")
    contradicting_evidence: List[Evidence] = Field(
        default_factory=list, description="Evidence against this"
    )
    confidence: float = Field(description="Overall confidence (0-1)")
    questions_to_investigate: List[str] = Field(
        default_factory=list, description="What to investigate next"
    )


class DailyNarrative(BaseModel):
    """Final generated narrative for a day."""

    date: datetime = Field(description="Date of narrative")
    headline: str = Field(description="Main headline")
    primary_narrative: str = Field(description="Primary explanation of market moves")
    supporting_narratives: List[str] = Field(
        default_factory=list, description="Secondary themes"
    )
    key_moves_explained: List[dict] = Field(
        default_factory=list, description="Specific asset stories"
    )
    prediction_market_insights: List[dict] = Field(
        default_factory=list, description="Relevant prediction market changes"
    )
    unexplained_moves: List[str] = Field(
        default_factory=list, description="Significant moves without clear explanation"
    )
    looking_ahead: Optional[str] = Field(default=None, description="Forward-looking insights")
    confidence_score: float = Field(description="Overall narrative confidence (0-1)")
    data_sources: List[str] = Field(description="Sources used")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
