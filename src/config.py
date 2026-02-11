"""Configuration management for the Market Narrative Agent."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class AssetConfig(BaseModel):
    """Configuration for assets to track."""

    indices: List[str] = Field(default_factory=lambda: ["^GSPC", "^IXIC"])
    stocks: List[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    )
    sector_etfs: List[str] = Field(
        default_factory=lambda: [
            "XLF",
            "XLE",
            "XLK",
            "XLV",
            "XLI",
            "XLY",
            "XLP",
            "XLB",
            "XLRE",
            "XLU",
            "XLC",
        ]
    )
    commodities: List[str] = Field(default_factory=lambda: ["CL=F", "GC=F"])
    volatility: List[str] = Field(default_factory=lambda: ["^VIX"])


class DataSourceConfig(BaseModel):
    """Configuration for data sources."""

    prices_enabled: bool = True
    news_enabled: bool = True
    predictions_enabled: bool = True


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    provider: str = "anthropic"  # or "openai"
    model_primary: str = "claude-3-5-sonnet-20250219"
    model_fast: str = "claude-3-5-haiku-20250219"
    max_tokens: int = 4000
    temperature: float = 0.7


class ProcessingConfig(BaseModel):
    """Configuration for data processing."""

    significance_threshold: float = 0.03  # 3% move
    volume_threshold: float = 1.5  # 1.5x average volume
    max_assets_analyzed: int = 10
    max_hypotheses_investigated: int = 2  # hypotheses to investigate per run
    max_tool_calls_per_hypothesis: int = 5  # tool calls allowed per hypothesis


class OutputConfig(BaseModel):
    """Configuration for output generation."""

    formats: List[str] = Field(default_factory=lambda: ["markdown", "json"])
    storage_path: Path = Field(default_factory=lambda: Path("./outputs"))


class CacheConfig(BaseModel):
    """Configuration for caching."""

    enabled: bool = True
    ttl_prices: int = 300  # 5 minutes
    ttl_news: int = 3600  # 1 hour
    ttl_predictions: int = 21600  # 6 hours


class Config(BaseModel):
    """Main configuration object."""

    assets: AssetConfig = Field(default_factory=AssetConfig)
    data_sources: DataSourceConfig = Field(default_factory=DataSourceConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # API keys from environment
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    newsapi_key: Optional[str] = None

    # Convenience properties for asset access
    @property
    def indices(self) -> List[str]:
        """Get list of index symbols."""
        return self.assets.indices

    @property
    def stocks(self) -> List[str]:
        """Get list of stock symbols."""
        return self.assets.stocks

    @property
    def sector_etfs(self) -> List[str]:
        """Get list of sector ETF symbols."""
        return self.assets.sector_etfs

    @property
    def commodities(self) -> List[str]:
        """Get list of commodity symbols."""
        return self.assets.commodities

    @property
    def volatility_indices(self) -> List[str]:
        """Get list of volatility index symbols."""
        return self.assets.volatility

    @property
    def primary_model(self) -> str:
        """Get primary LLM model name."""
        return self.llm.model_primary


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.

    Args:
        config_path: Path to config.yaml file. If None, looks in current directory.

    Returns:
        Config object with all settings
    """
    # Load environment variables
    load_dotenv()

    # Default config path
    if config_path is None:
        config_path = Path("config.yaml")
    else:
        config_path = Path(config_path)

    # Load from YAML if exists
    config_dict: Dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f) or {}

    # Add API keys from environment
    config_dict["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")
    config_dict["openai_api_key"] = os.getenv("OPENAI_API_KEY")
    config_dict["newsapi_key"] = os.getenv("NEWSAPI_KEY")

    # Create config object
    config = Config(**config_dict)

    return config
