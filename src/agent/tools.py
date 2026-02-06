"""Tool definitions for the market narrative agent.

These tools are called by the LLM during different phases of analysis.
"""

from datetime import datetime
from typing import Dict, List, Optional

from langchain_core.tools import tool
from loguru import logger

from src.analysis.processor import DataProcessor
from src.collectors.base import CollectionParams
from src.collectors.news import NewsCollector
from src.collectors.prediction import PredictionCollector
from src.collectors.price import PriceCollector, fetch_all_assets
from src.config import Config
from src.storage.models import MarketSnapshot


# Initialize collectors (will be injected by controller)
_price_collector: Optional[PriceCollector] = None
_news_collector: Optional[NewsCollector] = None
_prediction_collector: Optional[PredictionCollector] = None
_data_processor: Optional[DataProcessor] = None
_config: Optional[Config] = None


def initialize_tools(
    price_collector: PriceCollector,
    news_collector: NewsCollector,
    prediction_collector: PredictionCollector,
    data_processor: DataProcessor,
    config: Config,
):
    """Initialize tool dependencies.

    This must be called before using any tools.
    """
    global _price_collector, _news_collector, _prediction_collector, _data_processor, _config
    _price_collector = price_collector
    _news_collector = news_collector
    _prediction_collector = prediction_collector
    _data_processor = data_processor
    _config = config


# =============================================================================
# Phase 1 Tools: Initial Observation
# =============================================================================


@tool
async def get_market_overview(date: Optional[str] = None) -> Dict:
    """Get comprehensive market overview including indices, sectors, and major stocks.

    Args:
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dictionary with market snapshot including biggest movers, indices, sectors.
    """
    logger.info("Tool: get_market_overview called")

    if _price_collector is None or _data_processor is None or _config is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    # Parse date
    target_date = datetime.fromisoformat(date) if date else datetime.now()

    # Fetch all assets from config
    symbols = (
        _config.indices
        + _config.stocks
        + _config.sector_etfs
        + _config.commodities
        + _config.volatility_indices
    )

    params = CollectionParams(symbols=symbols, date=target_date)
    result = await _price_collector.collect(params)

    # Create market snapshot
    snapshot = _data_processor.create_market_snapshot(
        result.data,
        date=target_date,
        index_symbols=_config.indices,
        sector_symbols=_config.sector_etfs,
        volatility_symbols=_config.volatility_indices,
    )

    return {
        "date": snapshot.date.isoformat(),
        "major_indices": snapshot.major_indices,
        "biggest_gainers": [
            {
                "symbol": m.symbol,
                "name": m.name,
                "change_percent": m.change_percent,
                "volume_ratio": m.volume_ratio,
            }
            for m in snapshot.biggest_gainers[:10]
        ],
        "biggest_losers": [
            {
                "symbol": m.symbol,
                "name": m.name,
                "change_percent": m.change_percent,
                "volume_ratio": m.volume_ratio,
            }
            for m in snapshot.biggest_losers[:10]
        ],
        "sector_performance": snapshot.sector_performance,
        "market_breadth": snapshot.market_breadth,
        "volatility": snapshot.volatility,
    }


@tool
async def get_sector_returns(date: Optional[str] = None) -> Dict[str, float]:
    """Get performance for all sector ETFs.

    Args:
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dictionary mapping sector symbol to change percent.
    """
    logger.info("Tool: get_sector_returns called")

    if _price_collector is None or _config is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    target_date = datetime.fromisoformat(date) if date else datetime.now()

    params = CollectionParams(symbols=_config.sector_etfs, date=target_date)
    result = await _price_collector.collect(params)

    return {item["symbol"]: item["change_percent"] for item in result.data}


@tool
async def get_top_movers(n: int = 10, date: Optional[str] = None) -> Dict:
    """Get top N gainers and losers for the day.

    Args:
        n: Number of top movers to return (default 10)
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dictionary with 'gainers' and 'losers' lists.
    """
    logger.info(f"Tool: get_top_movers called (n={n})")

    if _price_collector is None or _data_processor is None or _config is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    target_date = datetime.fromisoformat(date) if date else datetime.now()

    # Fetch all stocks
    symbols = _config.stocks
    params = CollectionParams(symbols=symbols, date=target_date)
    result = await _price_collector.collect(params)

    # Get biggest movers
    gainers, losers = _data_processor.get_biggest_movers(result.data, n=n)

    return {
        "gainers": [
            {
                "symbol": m.symbol,
                "name": m.name,
                "change_percent": m.change_percent,
                "volume_ratio": m.volume_ratio,
            }
            for m in gainers
        ],
        "losers": [
            {
                "symbol": m.symbol,
                "name": m.name,
                "change_percent": m.change_percent,
                "volume_ratio": m.volume_ratio,
            }
            for m in losers
        ],
    }


@tool
async def get_news_headlines(limit: int = 50, keywords: Optional[List[str]] = None) -> List[Dict]:
    """Get recent news headlines, optionally filtered by keywords.

    Args:
        limit: Maximum number of headlines to return (default 50)
        keywords: Optional list of keywords to filter by

    Returns:
        List of news articles with title, source, published_at, summary.
    """
    logger.info(f"Tool: get_news_headlines called (limit={limit}, keywords={keywords})")

    if _news_collector is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    params = CollectionParams(limit=limit, keywords=keywords)
    result = await _news_collector.collect(params)

    return [
        {
            "title": article["title"],
            "source": article["source"],
            "published_at": article["published_at"].isoformat(),
            "summary": article.get("summary"),
            "url": article.get("url"),
        }
        for article in result.data
    ]


# =============================================================================
# Phase 3 Tools: Targeted Investigation
# =============================================================================


@tool
async def get_stock_details(symbol: str, date: Optional[str] = None) -> Dict:
    """Get detailed information about a specific stock.

    Args:
        symbol: Stock ticker symbol
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dictionary with price, volume, and change data.
    """
    logger.info(f"Tool: get_stock_details called (symbol={symbol})")

    if _price_collector is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    target_date = datetime.fromisoformat(date) if date else datetime.now()

    params = CollectionParams(symbols=[symbol], date=target_date)
    result = await _price_collector.collect(params)

    if not result.data:
        return {"error": f"No data found for {symbol}"}

    data = result.data[0]
    return {
        "symbol": data["symbol"],
        "name": data.get("name"),
        "price": data["price"],
        "change_percent": data["change_percent"],
        "change_absolute": data["change_absolute"],
        "volume": data.get("volume"),
        "volume_ratio": data.get("volume_ratio"),
    }


@tool
async def search_news(
    keywords: List[str], limit: int = 20, date: Optional[str] = None
) -> List[Dict]:
    """Search news articles for specific keywords.

    Args:
        keywords: List of keywords to search for
        limit: Maximum number of articles to return (default 20)
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        List of matching news articles.
    """
    logger.info(f"Tool: search_news called (keywords={keywords})")

    if _news_collector is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    target_date = datetime.fromisoformat(date) if date else None

    params = CollectionParams(keywords=keywords, limit=limit, date=target_date)
    result = await _news_collector.collect(params)

    return [
        {
            "title": article["title"],
            "source": article["source"],
            "published_at": article["published_at"].isoformat(),
            "summary": article.get("summary"),
            "keywords": article.get("keywords", []),
        }
        for article in result.data
    ]


@tool
async def get_prediction_markets(keywords: Optional[List[str]] = None, limit: int = 10) -> List[Dict]:
    """Get prediction market probabilities for relevant questions.

    Args:
        keywords: Optional keywords to filter markets
        limit: Maximum number of predictions to return (default 10)

    Returns:
        List of prediction markets with questions and probabilities.
    """
    logger.info(f"Tool: get_prediction_markets called (keywords={keywords})")

    if _prediction_collector is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    params = CollectionParams(keywords=keywords, limit=limit)
    result = await _prediction_collector.collect(params)

    return [
        {
            "question": pred["question"],
            "probability": pred["probability"],
            "platform": pred["platform"],
            "volume": pred.get("volume", 0),
            "url": pred.get("url"),
        }
        for pred in result.data
    ]


@tool
async def get_correlated_moves(
    symbol: str, threshold: float = 0.03, date: Optional[str] = None
) -> List[Dict]:
    """Find stocks with similar moves to the given symbol.

    Args:
        symbol: Stock ticker symbol
        threshold: Minimum absolute change percent to consider (default 3%)
        date: Optional date string (YYYY-MM-DD). Defaults to today.

    Returns:
        List of stocks with similar moves.
    """
    logger.info(f"Tool: get_correlated_moves called (symbol={symbol}, threshold={threshold})")

    if _price_collector is None or _data_processor is None or _config is None:
        raise RuntimeError("Tools not initialized. Call initialize_tools() first.")

    target_date = datetime.fromisoformat(date) if date else datetime.now()

    # Get the target stock's move
    target_params = CollectionParams(symbols=[symbol], date=target_date)
    target_result = await _price_collector.collect(target_params)

    if not target_result.data:
        return []

    target_change = target_result.data[0]["change_percent"]

    # Get all stocks
    all_params = CollectionParams(symbols=_config.stocks, date=target_date)
    all_result = await _price_collector.collect(all_params)

    # Find correlated moves (same direction, similar magnitude)
    correlated = []
    for data in all_result.data:
        if data["symbol"] == symbol:
            continue

        change = data["change_percent"]

        # Same direction and above threshold
        if (target_change > 0 and change > threshold) or (target_change < 0 and change < -threshold):
            correlated.append(
                {
                    "symbol": data["symbol"],
                    "name": data.get("name"),
                    "change_percent": change,
                    "volume_ratio": data.get("volume_ratio"),
                }
            )

    # Sort by magnitude
    correlated.sort(key=lambda x: abs(x["change_percent"]), reverse=True)

    return correlated[:10]


# =============================================================================
# Tool Registration
# =============================================================================


def get_all_tools():
    """Get all available tools for the agent."""
    return [
        # Phase 1: Observation
        get_market_overview,
        get_sector_returns,
        get_top_movers,
        get_news_headlines,
        # Phase 3: Investigation
        get_stock_details,
        search_news,
        get_prediction_markets,
        get_correlated_moves,
    ]
