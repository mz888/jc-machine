"""Data processor for analyzing market data and creating market snapshots."""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.config import ProcessingConfig
from src.storage.models import AssetMove, MarketSnapshot


class DataProcessor:
    """Processes raw market data into structured market snapshots."""

    def __init__(self, config: ProcessingConfig):
        """
        Initialize data processor.

        Args:
            config: Processing configuration with thresholds
        """
        self.config = config

    def create_asset_move(self, raw_data: Dict) -> AssetMove:
        """
        Convert raw price data to AssetMove model.

        Args:
            raw_data: Raw data dict from PriceCollector

        Returns:
            AssetMove object
        """
        return AssetMove(
            symbol=raw_data["symbol"],
            name=raw_data.get("name"),
            price=raw_data["price"],
            change_percent=raw_data["change_percent"],
            change_absolute=raw_data["change_absolute"],
            volume=raw_data.get("volume"),
            volume_ratio=raw_data.get("volume_ratio"),
        )

    def identify_significant_moves(
        self, price_data: List[Dict], include_volume: bool = True
    ) -> List[AssetMove]:
        """
        Identify assets with significant price or volume moves.

        Args:
            price_data: List of raw price data dicts
            include_volume: Whether to include volume criteria

        Returns:
            List of AssetMove objects with significant moves
        """
        significant = []

        for data in price_data:
            # Check price move threshold
            price_significant = (
                abs(data["change_percent"]) >= self.config.significance_threshold * 100
            )

            # Check volume threshold if applicable
            volume_significant = False
            if include_volume and data.get("volume_ratio"):
                volume_significant = data["volume_ratio"] >= self.config.volume_threshold

            # Include if either price or volume is significant
            if price_significant or volume_significant:
                asset_move = self.create_asset_move(data)
                significant.append(asset_move)

        logger.debug(
            f"Identified {len(significant)} significant moves from {len(price_data)} assets"
        )
        return significant

    def get_biggest_movers(
        self, price_data: List[Dict], n: int = 10
    ) -> tuple[List[AssetMove], List[AssetMove]]:
        """
        Get top N gainers and losers.

        Args:
            price_data: List of raw price data dicts
            n: Number of top movers to return

        Returns:
            Tuple of (biggest_gainers, biggest_losers)
        """
        # Convert to AssetMove objects
        moves = [self.create_asset_move(data) for data in price_data]

        # Sort by change percent
        moves_sorted = sorted(moves, key=lambda x: x.change_percent, reverse=True)

        # Get top gainers and losers
        biggest_gainers = moves_sorted[:n]
        biggest_losers = moves_sorted[-n:][::-1]  # Reverse to show worst first

        logger.debug(f"Top {n} gainers and losers identified")
        return biggest_gainers, biggest_losers

    def calculate_sector_performance(
        self, price_data: List[Dict], sector_symbols: List[str]
    ) -> Dict[str, float]:
        """
        Calculate performance for each sector ETF.

        Args:
            price_data: List of raw price data dicts
            sector_symbols: List of sector ETF symbols to include

        Returns:
            Dict mapping sector symbol to change percent
        """
        sector_performance = {}

        for data in price_data:
            if data["symbol"] in sector_symbols:
                sector_performance[data["symbol"]] = data["change_percent"]

        logger.debug(f"Calculated performance for {len(sector_performance)} sectors")
        return sector_performance

    def calculate_index_performance(
        self, price_data: List[Dict], index_symbols: List[str]
    ) -> Dict[str, float]:
        """
        Calculate performance for major indices.

        Args:
            price_data: List of raw price data dicts
            index_symbols: List of index symbols to include

        Returns:
            Dict mapping index symbol to change percent
        """
        index_performance = {}

        for data in price_data:
            if data["symbol"] in index_symbols:
                index_performance[data["symbol"]] = data["change_percent"]

        return index_performance

    def calculate_market_breadth(self, price_data: List[Dict]) -> Optional[Dict[str, int]]:
        """
        Calculate market breadth (advancers, decliners, unchanged).

        Args:
            price_data: List of raw price data dicts

        Returns:
            Dict with advancers, decliners, unchanged counts, or None
        """
        if not price_data:
            return None

        advancers = sum(1 for d in price_data if d["change_percent"] > 0)
        decliners = sum(1 for d in price_data if d["change_percent"] < 0)
        unchanged = sum(1 for d in price_data if d["change_percent"] == 0)

        return {"advancers": advancers, "decliners": decliners, "unchanged": unchanged}

    def extract_volatility(
        self, price_data: List[Dict], volatility_symbols: List[str]
    ) -> Optional[Dict[str, float]]:
        """
        Extract volatility index values (e.g., VIX).

        Args:
            price_data: List of raw price data dicts
            volatility_symbols: List of volatility symbols (e.g., ["^VIX"])

        Returns:
            Dict mapping volatility symbol to current price, or None
        """
        volatility = {}

        for data in price_data:
            if data["symbol"] in volatility_symbols:
                volatility[data["symbol"]] = data["price"]

        return volatility if volatility else None

    def create_market_snapshot(
        self,
        price_data: List[Dict],
        date: Optional[datetime] = None,
        index_symbols: Optional[List[str]] = None,
        sector_symbols: Optional[List[str]] = None,
        volatility_symbols: Optional[List[str]] = None,
    ) -> MarketSnapshot:
        """
        Create a complete market snapshot from raw price data.

        Args:
            price_data: List of raw price data dicts from PriceCollector
            date: Date of snapshot (defaults to now)
            index_symbols: List of index symbols (e.g., ["^GSPC", "^IXIC"])
            sector_symbols: List of sector ETF symbols
            volatility_symbols: List of volatility symbols (e.g., ["^VIX"])

        Returns:
            MarketSnapshot object
        """
        if not price_data:
            logger.warning("No price data provided for market snapshot")
            # Return empty snapshot
            return MarketSnapshot(
                date=date or datetime.now(),
                major_indices={},
                biggest_gainers=[],
                biggest_losers=[],
                sector_performance={},
                market_breadth=None,
                volatility=None,
            )

        logger.info(f"Creating market snapshot from {len(price_data)} assets")

        # Get biggest movers (limit by config)
        n_movers = min(self.config.max_assets_analyzed, len(price_data))
        biggest_gainers, biggest_losers = self.get_biggest_movers(price_data, n=n_movers)

        # Calculate index performance
        major_indices = {}
        if index_symbols:
            major_indices = self.calculate_index_performance(price_data, index_symbols)

        # Calculate sector performance
        sector_performance = {}
        if sector_symbols:
            sector_performance = self.calculate_sector_performance(
                price_data, sector_symbols
            )

        # Calculate market breadth
        market_breadth = self.calculate_market_breadth(price_data)

        # Extract volatility
        volatility = None
        if volatility_symbols:
            volatility = self.extract_volatility(price_data, volatility_symbols)

        snapshot = MarketSnapshot(
            date=date or datetime.now(),
            major_indices=major_indices,
            biggest_gainers=biggest_gainers,
            biggest_losers=biggest_losers,
            sector_performance=sector_performance,
            market_breadth=market_breadth,
            volatility=volatility,
        )

        logger.info(
            f"Market snapshot created: {len(biggest_gainers)} gainers, "
            f"{len(biggest_losers)} losers, {len(sector_performance)} sectors"
        )

        return snapshot

    def filter_by_significance(
        self, snapshot: MarketSnapshot, threshold: Optional[float] = None
    ) -> tuple[List[AssetMove], List[AssetMove]]:
        """
        Filter snapshot movers by significance threshold.

        Args:
            snapshot: MarketSnapshot to filter
            threshold: Custom threshold (uses config default if None)

        Returns:
            Tuple of (significant_gainers, significant_losers)
        """
        threshold_pct = (
            threshold * 100 if threshold else self.config.significance_threshold * 100
        )

        significant_gainers = [
            move for move in snapshot.biggest_gainers if move.change_percent >= threshold_pct
        ]

        significant_losers = [
            move
            for move in snapshot.biggest_losers
            if abs(move.change_percent) >= threshold_pct
        ]

        logger.debug(
            f"Filtered to {len(significant_gainers)} significant gainers "
            f"and {len(significant_losers)} significant losers (threshold: {threshold_pct}%)"
        )

        return significant_gainers, significant_losers
