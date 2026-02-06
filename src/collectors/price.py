"""Price data collector using yfinance."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import yfinance as yf
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.collectors.base import CollectionParams, CollectionResult, DataCollector


class PriceCollector(DataCollector):
    """Collects price data for stocks, indices, ETFs, and commodities using yfinance."""

    def __init__(self, cache_enabled: bool = True):
        """
        Initialize price collector.

        Args:
            cache_enabled: Whether to enable caching
        """
        super().__init__(cache_enabled)
        self._cache: Dict[str, Dict] = {}

    @property
    def cache_ttl(self) -> int:
        """Cache TTL in seconds (5 minutes)."""
        return 300

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "yfinance"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _fetch_ticker_data(
        self, symbol: str, period: str = "5d", interval: str = "1d"
    ) -> Optional[Dict]:
        """
        Fetch data for a single ticker with retry logic.

        Args:
            symbol: Ticker symbol
            period: Time period to fetch (default: 5 days for calculating returns)
            interval: Data interval (default: 1 day)

        Returns:
            Dict with ticker data or None if fetch fails
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            # Get latest and previous close prices
            latest = hist.iloc[-1]
            previous = hist.iloc[-2] if len(hist) > 1 else None

            # Calculate return
            if previous is not None:
                change_absolute = latest["Close"] - previous["Close"]
                change_percent = (change_absolute / previous["Close"]) * 100
            else:
                change_absolute = 0.0
                change_percent = 0.0

            # Calculate volume ratio (vs average volume over period)
            avg_volume = hist["Volume"].mean() if len(hist) > 1 else latest["Volume"]
            volume_ratio = (
                latest["Volume"] / avg_volume if avg_volume > 0 else 1.0
            )

            # Get ticker info for name (may not always be available)
            name = None
            try:
                info = ticker.info
                name = info.get("longName") or info.get("shortName")
            except Exception as e:
                logger.debug(f"Could not fetch info for {symbol}: {e}")

            return {
                "symbol": symbol,
                "name": name,
                "price": float(latest["Close"]),
                "change_absolute": float(change_absolute),
                "change_percent": float(change_percent),
                "volume": float(latest["Volume"]) if latest["Volume"] > 0 else None,
                "volume_ratio": float(volume_ratio),
                "timestamp": latest.name.to_pydatetime(),
            }

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def collect(self, params: CollectionParams) -> CollectionResult:
        """
        Collect price data for specified symbols.

        Args:
            params: Collection parameters with symbols list

        Returns:
            CollectionResult with price data
        """
        if not params.symbols:
            logger.warning("No symbols provided for price collection")
            return CollectionResult(
                data=[],
                timestamp=datetime.now(),
                source=self.source_name,
                metadata={"error": "No symbols provided"},
            )

        logger.info(f"Collecting price data for {len(params.symbols)} symbols")

        results = []
        errors = []

        for symbol in params.symbols:
            # Check cache if enabled
            cache_key = f"{symbol}_{params.date or 'latest'}"
            if self.cache_enabled and cache_key in self._cache:
                logger.debug(f"Using cached data for {symbol}")
                results.append(self._cache[cache_key])
                continue

            # Fetch data
            data = self._fetch_ticker_data(symbol)

            if data:
                results.append(data)
                if self.cache_enabled:
                    self._cache[cache_key] = data
            else:
                errors.append(symbol)

        # Log summary
        logger.info(
            f"Successfully fetched {len(results)}/{len(params.symbols)} symbols"
        )
        if errors:
            logger.warning(f"Failed to fetch: {', '.join(errors)}")

        return CollectionResult(
            data=results,
            timestamp=datetime.now(),
            source=self.source_name,
            metadata={
                "symbols_requested": len(params.symbols),
                "symbols_fetched": len(results),
                "symbols_failed": errors,
            },
        )

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.debug("Price collector cache cleared")


async def fetch_all_assets(
    collector: PriceCollector,
    indices: List[str],
    stocks: List[str],
    sector_etfs: List[str],
    commodities: List[str],
    volatility: List[str],
) -> CollectionResult:
    """
    Convenience function to fetch all asset types.

    Args:
        collector: PriceCollector instance
        indices: List of index symbols
        stocks: List of stock symbols
        sector_etfs: List of sector ETF symbols
        commodities: List of commodity symbols
        volatility: List of volatility symbols (e.g., VIX)

    Returns:
        CollectionResult with all asset data
    """
    all_symbols = indices + stocks + sector_etfs + commodities + volatility

    params = CollectionParams(symbols=all_symbols)

    return await collector.collect(params)
