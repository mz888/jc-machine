"""Prediction market data collector.

Collects prediction probabilities from multiple prediction market platforms:
- Manifold Markets (free, unlimited)
- Polymarket (via public API, free tier)
"""

from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.collectors.base import CollectionParams, CollectionResult, DataCollector


class PredictionCollector(DataCollector):
    """Collects prediction market data from multiple platforms."""

    def __init__(
        self,
        platforms: Optional[List[str]] = None,
        cache_enabled: bool = True,
        timeout: int = 10,
    ):
        """
        Initialize prediction market collector.

        Args:
            platforms: List of platforms to query (default: ["manifold", "polymarket"])
            cache_enabled: Whether to enable caching
            timeout: Request timeout in seconds
        """
        super().__init__(cache_enabled=cache_enabled)
        self.platforms = platforms or ["manifold", "polymarket"]
        self.timeout = timeout
        self._cache: Dict[str, Dict] = {}

        # API endpoints
        self.manifold_api = "https://api.manifold.markets/v0"
        self.polymarket_api = "https://gamma-api.polymarket.com"

    @property
    def source_name(self) -> str:
        """Source identifier for this collector."""
        return "prediction_markets"

    @property
    def cache_ttl(self) -> int:
        """Cache time-to-live in seconds (1 hour)."""
        return 3600

    async def collect(self, params: CollectionParams) -> CollectionResult:
        """
        Collect prediction market data.

        Args:
            params: Collection parameters including keywords for filtering

        Returns:
            CollectionResult with predictions
        """
        cache_key = self._get_cache_key(params)

        # Check cache
        if self.cache_enabled and cache_key in self._cache:
            logger.info("Retrieved prediction data from cache")
            return CollectionResult(
                data=self._cache[cache_key],
                timestamp=datetime.now(),
                source=self.source_name,
                metadata={"cached": True},
            )

        logger.info(f"Fetching predictions from platforms: {self.platforms}")

        predictions = []
        metadata = {
            "platforms_used": self.platforms,
            "keywords": params.keywords or [],
            "total_predictions": 0,
        }

        # Fetch from each platform
        for platform in self.platforms:
            try:
                if platform == "manifold":
                    platform_predictions = await self._fetch_manifold(params)
                elif platform == "polymarket":
                    platform_predictions = await self._fetch_polymarket(params)
                else:
                    logger.warning(f"Unknown platform: {platform}")
                    continue

                predictions.extend(platform_predictions)
                logger.info(f"Fetched {len(platform_predictions)} predictions from {platform}")

            except Exception as e:
                logger.error(f"Error fetching from {platform}: {e}")
                # Continue with other platforms

        # Sort by volume/popularity (if available) or last_updated
        predictions.sort(
            key=lambda x: (x.get("volume", 0), x.get("last_updated", datetime.min)),
            reverse=True,
        )

        # Apply limit
        if params.limit:
            predictions = predictions[: params.limit]

        metadata["total_predictions"] = len(predictions)
        metadata["cached"] = False

        # Cache results
        if self.cache_enabled:
            self._cache[cache_key] = predictions

        logger.info(f"Collected {len(predictions)} total predictions")

        return CollectionResult(
            source=self.source_name,
            timestamp=datetime.now(),
            data=predictions,
            metadata=metadata,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _fetch_manifold(self, params: CollectionParams) -> List[Dict]:
        """
        Fetch predictions from Manifold Markets.

        Args:
            params: Collection parameters

        Returns:
            List of prediction dictionaries
        """
        predictions = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Search for relevant markets
            if params.keywords:
                # Search each keyword
                for keyword in params.keywords:
                    url = f"{self.manifold_api}/search-markets"
                    params_dict = {"term": keyword, "limit": 20}

                    response = await client.get(url, params=params_dict)
                    response.raise_for_status()

                    markets = response.json()

                    for market in markets:
                        prediction = self._parse_manifold_market(market)
                        if prediction:
                            predictions.append(prediction)
            else:
                # Get recently active markets if no keywords specified
                url = f"{self.manifold_api}/markets"
                params_dict = {"limit": 20, "sort": "last-bet-time"}

                response = await client.get(url, params=params_dict)
                response.raise_for_status()

                markets = response.json()

                for market in markets:
                    prediction = self._parse_manifold_market(market)
                    if prediction:
                        predictions.append(prediction)

        # Remove duplicates
        seen_questions = set()
        unique_predictions = []
        for pred in predictions:
            q = pred["question"].lower()
            if q not in seen_questions:
                seen_questions.add(q)
                unique_predictions.append(pred)

        return unique_predictions

    def _parse_manifold_market(self, market: Dict) -> Optional[Dict]:
        """Parse Manifold market data into standard format."""
        try:
            # Only handle binary markets for simplicity
            if market.get("outcomeType") != "BINARY":
                return None

            return {
                "question": market["question"],
                "probability": market.get("probability", 0.5),
                "platform": "Manifold Markets",
                "url": market.get("url", ""),
                "last_updated": datetime.fromtimestamp(
                    market.get("lastUpdatedTime", 0) / 1000
                ),
                "volume": market.get("volume24Hours", 0),
                "created_time": datetime.fromtimestamp(market.get("createdTime", 0) / 1000),
                "close_time": (
                    datetime.fromtimestamp(market["closeTime"] / 1000)
                    if market.get("closeTime")
                    else None
                ),
            }
        except Exception as e:
            logger.warning(f"Error parsing Manifold market: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _fetch_polymarket(self, params: CollectionParams) -> List[Dict]:
        """
        Fetch predictions from Polymarket.

        Args:
            params: Collection parameters

        Returns:
            List of prediction dictionaries
        """
        predictions = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Fetch open (non-closed) markets
            url = f"{self.polymarket_api}/markets"
            params_dict = {"closed": "false", "limit": 100}

            # Add search filter if keywords provided
            if params.keywords:
                # Polymarket doesn't have direct keyword search in the API
                # We'll filter client-side after fetching
                pass

            response = await client.get(url, params=params_dict)
            response.raise_for_status()

            markets = response.json()

            # Filter by keywords if provided
            if params.keywords:
                keywords_lower = [k.lower() for k in params.keywords]
                filtered_markets = []
                for market in markets:
                    text = f"{market.get('question', '')} {market.get('description', '')}".lower()
                    if any(keyword in text for keyword in keywords_lower):
                        filtered_markets.append(market)
                markets = filtered_markets

            # Parse each market
            for market in markets:
                prediction = self._parse_polymarket_market(market)
                if prediction:
                    predictions.append(prediction)

        # Remove duplicates by question
        seen_questions = set()
        unique_predictions = []
        for pred in predictions:
            q = pred["question"].lower()
            if q not in seen_questions:
                seen_questions.add(q)
                unique_predictions.append(pred)

        return unique_predictions

    def _parse_polymarket_market(self, market: Dict) -> Optional[Dict]:
        """Parse Polymarket market data into standard format."""
        try:
            # Parse outcomes and prices
            import json

            outcomes = json.loads(market.get("outcomes", "[]"))
            outcome_prices = json.loads(market.get("outcomePrices", "[]"))

            # Only handle binary markets (Yes/No)
            if len(outcomes) != 2 or len(outcome_prices) != 2:
                return None

            # First outcome is typically "Yes", use its price as probability
            probability = float(outcome_prices[0]) if outcome_prices[0] else 0.5

            # Parse end date
            end_date_str = market.get("endDate")
            close_time = None
            if end_date_str:
                try:
                    close_time = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            return {
                "question": market["question"],
                "probability": probability,
                "platform": "Polymarket",
                "url": f"https://polymarket.com/event/{market.get('slug', '')}",
                "last_updated": datetime.now(),  # Polymarket doesn't provide last update time
                "volume": float(market.get("volume", 0)),
                "created_time": datetime.now(),  # Not available in API response
                "close_time": close_time,
            }
        except Exception as e:
            logger.warning(f"Error parsing Polymarket market: {e}")
            return None

    def _get_cache_key(self, params: CollectionParams) -> str:
        """Generate cache key from parameters."""
        keywords_str = "_".join(sorted(params.keywords)) if params.keywords else "none"
        platforms_str = "_".join(sorted(self.platforms))
        return f"predictions_{platforms_str}_{keywords_str}_{params.limit}"

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.debug("Prediction collector cache cleared")
