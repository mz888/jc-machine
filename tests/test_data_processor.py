"""Tests for DataProcessor."""

import pytest
from datetime import datetime

from src.analysis.processor import DataProcessor
from src.config import ProcessingConfig
from src.storage.models import MarketSnapshot


class TestDataProcessor:
    """Test suite for DataProcessor."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ProcessingConfig(
            significance_threshold=0.03,  # 3%
            volume_threshold=1.5,
            max_assets_analyzed=10,
        )

    @pytest.fixture
    def processor(self, config):
        """Create DataProcessor instance."""
        return DataProcessor(config)

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data."""
        return [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 150.0,
                "change_percent": 2.5,
                "change_absolute": 3.75,
                "volume": 1000000,
                "volume_ratio": 1.2,
                "timestamp": datetime.now(),
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft",
                "price": 300.0,
                "change_percent": -4.2,
                "change_absolute": -12.6,
                "volume": 2000000,
                "volume_ratio": 2.0,
                "timestamp": datetime.now(),
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet",
                "price": 100.0,
                "change_percent": 0.5,
                "change_absolute": 0.5,
                "volume": 500000,
                "volume_ratio": 0.8,
                "timestamp": datetime.now(),
            },
            {
                "symbol": "^GSPC",
                "name": "S&P 500",
                "price": 4500.0,
                "change_percent": 1.0,
                "change_absolute": 45.0,
                "volume": None,
                "volume_ratio": None,
                "timestamp": datetime.now(),
            },
            {
                "symbol": "XLK",
                "name": "Technology Sector",
                "price": 150.0,
                "change_percent": -2.0,
                "change_absolute": -3.0,
                "volume": 100000,
                "volume_ratio": 1.5,
                "timestamp": datetime.now(),
            },
            {
                "symbol": "^VIX",
                "name": "VIX",
                "price": 15.5,
                "change_percent": 5.0,
                "change_absolute": 0.75,
                "volume": None,
                "volume_ratio": None,
                "timestamp": datetime.now(),
            },
        ]

    def test_create_asset_move(self, processor, sample_price_data):
        """Test converting raw data to AssetMove."""
        raw = sample_price_data[0]
        move = processor.create_asset_move(raw)

        assert move.symbol == "AAPL"
        assert move.name == "Apple Inc."
        assert move.price == 150.0
        assert move.change_percent == 2.5
        assert move.change_absolute == 3.75
        assert move.volume == 1000000
        assert move.volume_ratio == 1.2

    def test_identify_significant_moves(self, processor, sample_price_data):
        """Test identifying significant price moves."""
        # With 3% threshold, MSFT (-4.2%) should be significant
        # AAPL (2.5%) should not be
        significant = processor.identify_significant_moves(sample_price_data)

        # Should find MSFT (-4.2%) and ^VIX (5.0%)
        symbols = [move.symbol for move in significant]
        assert "MSFT" in symbols
        assert "^VIX" in symbols
        assert "AAPL" not in symbols  # 2.5% < 3%
        assert "GOOGL" not in symbols  # 0.5% < 3%

    def test_identify_significant_moves_volume(self, processor, sample_price_data):
        """Test identifying significant volume moves."""
        # MSFT has volume_ratio of 2.0 (> 1.5 threshold)
        significant = processor.identify_significant_moves(
            sample_price_data, include_volume=True
        )

        symbols = [move.symbol for move in significant]
        assert "MSFT" in symbols  # High volume AND price move
        assert "XLK" in symbols  # Volume 1.5x exactly

    def test_get_biggest_movers(self, processor, sample_price_data):
        """Test getting top gainers and losers."""
        gainers, losers = processor.get_biggest_movers(sample_price_data, n=3)

        # Check gainers (sorted descending)
        assert len(gainers) <= 3
        assert gainers[0].symbol == "^VIX"  # +5.0%
        assert gainers[1].symbol == "AAPL"  # +2.5%

        # Check losers (sorted ascending by absolute value)
        assert len(losers) <= 3
        assert losers[0].symbol == "MSFT"  # -4.2%
        assert losers[1].symbol == "XLK"  # -2.0%

    def test_calculate_sector_performance(self, processor, sample_price_data):
        """Test calculating sector performance."""
        sector_symbols = ["XLK", "XLF"]
        performance = processor.calculate_sector_performance(
            sample_price_data, sector_symbols
        )

        assert "XLK" in performance
        assert performance["XLK"] == -2.0
        assert "XLF" not in performance  # Not in sample data

    def test_calculate_index_performance(self, processor, sample_price_data):
        """Test calculating index performance."""
        index_symbols = ["^GSPC", "^IXIC"]
        performance = processor.calculate_index_performance(sample_price_data, index_symbols)

        assert "^GSPC" in performance
        assert performance["^GSPC"] == 1.0
        assert "^IXIC" not in performance  # Not in sample data

    def test_calculate_market_breadth(self, processor, sample_price_data):
        """Test calculating market breadth."""
        breadth = processor.calculate_market_breadth(sample_price_data)

        assert breadth is not None
        assert "advancers" in breadth
        assert "decliners" in breadth
        assert "unchanged" in breadth

        # From sample data: AAPL, ^GSPC, ^VIX are up (3)
        # MSFT, XLK are down (2)
        # GOOGL is up (1)
        assert breadth["advancers"] == 4  # Positive changes
        assert breadth["decliners"] == 2  # Negative changes
        assert breadth["unchanged"] == 0  # Zero changes

    def test_calculate_market_breadth_empty(self, processor):
        """Test market breadth with empty data."""
        breadth = processor.calculate_market_breadth([])
        assert breadth is None

    def test_extract_volatility(self, processor, sample_price_data):
        """Test extracting volatility indices."""
        volatility_symbols = ["^VIX"]
        volatility = processor.extract_volatility(sample_price_data, volatility_symbols)

        assert volatility is not None
        assert "^VIX" in volatility
        assert volatility["^VIX"] == 15.5

    def test_extract_volatility_none(self, processor, sample_price_data):
        """Test extracting volatility when not present."""
        volatility_symbols = ["^VVIX"]  # Not in sample data
        volatility = processor.extract_volatility(sample_price_data, volatility_symbols)

        assert volatility is None or len(volatility) == 0

    def test_create_market_snapshot(self, processor, sample_price_data):
        """Test creating a complete market snapshot."""
        snapshot = processor.create_market_snapshot(
            sample_price_data,
            index_symbols=["^GSPC"],
            sector_symbols=["XLK"],
            volatility_symbols=["^VIX"],
        )

        assert isinstance(snapshot, MarketSnapshot)
        assert isinstance(snapshot.date, datetime)
        assert len(snapshot.biggest_gainers) > 0
        assert len(snapshot.biggest_losers) > 0
        assert "^GSPC" in snapshot.major_indices
        assert "XLK" in snapshot.sector_performance
        assert snapshot.market_breadth is not None
        assert snapshot.volatility is not None
        assert "^VIX" in snapshot.volatility

    def test_create_market_snapshot_empty(self, processor):
        """Test creating market snapshot with empty data."""
        snapshot = processor.create_market_snapshot([])

        assert isinstance(snapshot, MarketSnapshot)
        assert len(snapshot.biggest_gainers) == 0
        assert len(snapshot.biggest_losers) == 0
        assert len(snapshot.major_indices) == 0
        assert len(snapshot.sector_performance) == 0

    def test_create_market_snapshot_limited_movers(self, processor):
        """Test that max_assets_analyzed limit is respected."""
        # Create more than 10 assets
        large_dataset = [
            {
                "symbol": f"STOCK{i}",
                "name": f"Company {i}",
                "price": 100.0 + i,
                "change_percent": float(i - 10),
                "change_absolute": float(i - 10),
                "volume": 1000000,
                "volume_ratio": 1.0,
                "timestamp": datetime.now(),
            }
            for i in range(20)
        ]

        snapshot = processor.create_market_snapshot(large_dataset)

        # Should limit to max_assets_analyzed (10)
        assert len(snapshot.biggest_gainers) <= 10
        assert len(snapshot.biggest_losers) <= 10

    def test_filter_by_significance(self, processor, sample_price_data):
        """Test filtering snapshot by significance."""
        snapshot = processor.create_market_snapshot(sample_price_data)

        significant_gainers, significant_losers = processor.filter_by_significance(snapshot)

        # With 3% threshold, only moves >= 3% should be included
        for gainer in significant_gainers:
            assert gainer.change_percent >= 3.0

        for loser in significant_losers:
            assert abs(loser.change_percent) >= 3.0

    def test_filter_by_custom_threshold(self, processor, sample_price_data):
        """Test filtering with custom threshold."""
        snapshot = processor.create_market_snapshot(sample_price_data)

        # Use 1% threshold instead of default 3%
        significant_gainers, significant_losers = processor.filter_by_significance(
            snapshot, threshold=0.01
        )

        # Should include more moves with lower threshold
        assert len(significant_gainers) >= 1
        assert len(significant_losers) >= 1

        # AAPL (2.5%) should now be included
        gainer_symbols = [g.symbol for g in significant_gainers]
        assert "AAPL" in gainer_symbols

    def test_snapshot_date(self, processor, sample_price_data):
        """Test that snapshot date can be set."""
        test_date = datetime(2024, 1, 1, 12, 0, 0)
        snapshot = processor.create_market_snapshot(sample_price_data, date=test_date)

        assert snapshot.date == test_date

    def test_snapshot_date_default(self, processor, sample_price_data):
        """Test that snapshot date defaults to now."""
        before = datetime.now()
        snapshot = processor.create_market_snapshot(sample_price_data)
        after = datetime.now()

        assert before <= snapshot.date <= after

    def test_movers_ordering(self, processor, sample_price_data):
        """Test that movers are correctly ordered."""
        gainers, losers = processor.get_biggest_movers(sample_price_data, n=10)

        # Gainers should be in descending order
        for i in range(len(gainers) - 1):
            assert gainers[i].change_percent >= gainers[i + 1].change_percent

        # Losers should be in ascending order (most negative first)
        for i in range(len(losers) - 1):
            assert losers[i].change_percent <= losers[i + 1].change_percent


if __name__ == "__main__":
    # Can run tests directly for quick debugging
    pytest.main([__file__, "-v"])
