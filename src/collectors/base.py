"""Base classes for data collectors."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CollectionResult(BaseModel):
    """Result from a data collection operation."""

    data: List[Dict[str, Any]] = Field(description="Collected data records")
    timestamp: datetime = Field(description="When data was collected")
    source: str = Field(description="Data source identifier")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about collection"
    )


class CollectionParams(BaseModel):
    """Parameters for data collection."""

    date: Optional[datetime] = None
    symbols: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    limit: Optional[int] = None


class DataCollector(ABC):
    """Abstract base class for data collectors."""

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize collector.

        Args:
            cache_enabled: Whether to enable caching for this collector
        """
        self.cache_enabled = cache_enabled

    @abstractmethod
    async def collect(self, params: CollectionParams) -> CollectionResult:
        """
        Collect data from source.

        Args:
            params: Collection parameters

        Returns:
            CollectionResult with data and metadata
        """
        pass

    @property
    @abstractmethod
    def cache_ttl(self) -> int:
        """
        Time-to-live for cached data in seconds.

        Returns:
            TTL in seconds
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        Name of the data source.

        Returns:
            Source name string
        """
        pass
