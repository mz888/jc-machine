"""Data collectors for market data, news, and prediction markets."""

from src.collectors.base import CollectionResult, DataCollector
from src.collectors.news import NewsCollector
from src.collectors.prediction import PredictionCollector
from src.collectors.price import PriceCollector, fetch_all_assets

__all__ = [
    "DataCollector",
    "CollectionResult",
    "PriceCollector",
    "NewsCollector",
    "PredictionCollector",
    "fetch_all_assets",
]
