"""Tests for PriceCollector."""

import pytest
from datetime import datetime

from src.collectors.base import CollectionParams
from src.collectors.price import PriceCollector, fetch_all_assets


class TestPriceCollector:
    """Test suite for PriceCollector."""

    @pytest.fixture
    def collector(self):
        """Create a PriceCollector instance."""
        return PriceCollector(cache_enabled=True)

    @pytest.fixture
    def test_symbols(self):
        """Provide test symbols."""
        return ["AAPL", "MSFT", "^GSPC"]  # Stock, stock, index

    @pytest.mark.asyncio
    async def test_collect_basic(self, collector, test_symbols):
        """Test basic data collection."""
        params = CollectionParams(symbols=test_symbols)
        result = await collector.collect(params)

        # Verify result structure
        assert result is not None
        assert result.source == "yfinance"
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.data, list)
        assert isinstance(result.metadata, dict)

        # Should have fetched at least some symbols
        assert len(result.data) > 0
        assert result.metadata["symbols_requested"] == len(test_symbols)

    @pytest.mark.asyncio
    async def test_data_structure(self, collector):
        """Test that returned data has correct structure."""
        params = CollectionParams(symbols=["AAPL"])
        result = await collector.collect(params)

        # Should have data for AAPL
        assert len(result.data) > 0

        data = result.data[0]

        # Verify all required fields
        assert "symbol" in data
        assert "price" in data
        assert "change_absolute" in data
        assert "change_percent" in data
        assert "volume_ratio" in data
        assert "timestamp" in data

        # Verify data types
        assert isinstance(data["symbol"], str)
        assert isinstance(data["price"], float)
        assert isinstance(data["change_absolute"], float)
        assert isinstance(data["change_percent"], float)
        assert isinstance(data["volume_ratio"], float)
        assert isinstance(data["timestamp"], datetime)

        # Price should be positive
        assert data["price"] > 0

    @pytest.mark.asyncio
    async def test_invalid_symbol(self, collector):
        """Test handling of invalid symbols."""
        params = CollectionParams(symbols=["INVALID_SYMBOL_XYZZZ"])
        result = await collector.collect(params)

        # Should handle gracefully
        assert result is not None
        assert len(result.data) == 0
        assert len(result.metadata.get("symbols_failed", [])) > 0

    @pytest.mark.asyncio
    async def test_empty_symbols(self, collector):
        """Test handling of empty symbols list."""
        params = CollectionParams(symbols=[])
        result = await collector.collect(params)

        # Should handle gracefully
        assert result is not None
        assert len(result.data) == 0
        assert "error" in result.metadata

    @pytest.mark.asyncio
    async def test_cache(self, collector):
        """Test caching functionality."""
        params = CollectionParams(symbols=["AAPL"])

        # First call - should fetch from API
        result1 = await collector.collect(params)
        assert len(result1.data) > 0

        # Second call - should use cache
        result2 = await collector.collect(params)
        assert len(result2.data) > 0

        # Data should be identical (from cache)
        assert result1.data[0]["symbol"] == result2.data[0]["symbol"]
        assert result1.data[0]["price"] == result2.data[0]["price"]

        # Clear cache
        collector.clear_cache()

        # Third call - should fetch again
        result3 = await collector.collect(params)
        assert len(result3.data) > 0

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, collector, test_symbols):
        """Test collecting multiple symbols at once."""
        params = CollectionParams(symbols=test_symbols)
        result = await collector.collect(params)

        # Should fetch most/all symbols
        assert len(result.data) >= len(test_symbols) - 1  # Allow 1 failure
        assert result.metadata["symbols_requested"] == len(test_symbols)
        assert result.metadata["symbols_fetched"] >= len(test_symbols) - 1

    @pytest.mark.asyncio
    async def test_sector_etf(self, collector):
        """Test collecting sector ETF data."""
        params = CollectionParams(symbols=["XLK"])  # Technology sector ETF
        result = await collector.collect(params)

        assert len(result.data) > 0
        data = result.data[0]
        assert data["symbol"] == "XLK"
        assert data["price"] > 0

    @pytest.mark.asyncio
    async def test_commodity(self, collector):
        """Test collecting commodity data."""
        params = CollectionParams(symbols=["GC=F"])  # Gold futures
        result = await collector.collect(params)

        # Commodity symbols sometimes have issues, so just verify structure
        assert result is not None
        if len(result.data) > 0:
            data = result.data[0]
            assert "symbol" in data
            assert "price" in data

    @pytest.mark.asyncio
    async def test_vix(self, collector):
        """Test collecting VIX (volatility index) data."""
        params = CollectionParams(symbols=["^VIX"])
        result = await collector.collect(params)

        # VIX should be available
        assert len(result.data) > 0
        data = result.data[0]
        assert data["symbol"] == "^VIX"
        assert data["price"] > 0
        # VIX typically ranges from 10-80
        assert 5 < data["price"] < 100

    @pytest.mark.asyncio
    async def test_fetch_all_assets(self, collector):
        """Test the fetch_all_assets helper function."""
        result = await fetch_all_assets(
            collector=collector,
            indices=["^GSPC"],
            stocks=["AAPL", "MSFT"],
            sector_etfs=["XLK"],
            commodities=["GC=F"],
            volatility=["^VIX"],
        )

        # Should fetch most symbols
        assert len(result.data) >= 4  # At least most symbols should work
        assert result.metadata["symbols_requested"] == 6

    @pytest.mark.asyncio
    async def test_return_calculation(self, collector):
        """Test that returns are calculated correctly."""
        params = CollectionParams(symbols=["AAPL"])
        result = await collector.collect(params)

        assert len(result.data) > 0
        data = result.data[0]

        # Verify return calculation consistency
        # change_percent should equal (change_absolute / previous_price) * 100
        # We can't verify exact numbers without knowing previous price,
        # but we can verify the relationship
        if data["change_percent"] != 0:
            # If there's a change, absolute should also be non-zero
            assert data["change_absolute"] != 0

    @pytest.mark.asyncio
    async def test_volume_ratio(self, collector):
        """Test that volume ratio is calculated."""
        params = CollectionParams(symbols=["AAPL"])
        result = await collector.collect(params)

        assert len(result.data) > 0
        data = result.data[0]

        # Volume ratio should be positive
        assert data["volume_ratio"] > 0
        # Should typically be between 0.1 and 10 (unless extreme volume day)
        assert 0.01 < data["volume_ratio"] < 20

    def test_cache_ttl(self, collector):
        """Test that cache TTL is set correctly."""
        assert collector.cache_ttl == 300  # 5 minutes

    def test_source_name(self, collector):
        """Test that source name is correct."""
        assert collector.source_name == "yfinance"


if __name__ == "__main__":
    # Can run tests directly for quick debugging
    pytest.main([__file__, "-v"])
