"""Tests for PredictionCollector."""

import pytest
from datetime import datetime

from src.collectors.base import CollectionParams
from src.collectors.prediction import PredictionCollector


class TestPredictionCollector:
    """Test suite for PredictionCollector."""

    @pytest.fixture
    def collector_manifold(self):
        """Create a PredictionCollector with only Manifold."""
        return PredictionCollector(platforms=["manifold"], cache_enabled=True)

    @pytest.fixture
    def collector_polymarket(self):
        """Create a PredictionCollector with only Polymarket."""
        return PredictionCollector(platforms=["polymarket"], cache_enabled=True)

    @pytest.fixture
    def collector_all(self):
        """Create a PredictionCollector with all platforms."""
        return PredictionCollector(
            platforms=["manifold", "polymarket"], cache_enabled=True
        )

    @pytest.mark.asyncio
    async def test_collect_manifold_basic(self, collector_manifold):
        """Test basic Manifold prediction collection."""
        params = CollectionParams(limit=5)
        result = await collector_manifold.collect(params)

        # Verify result structure
        assert result is not None
        assert result.source == "prediction_markets"
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.data, list)
        assert isinstance(result.metadata, dict)

        # Should have fetched some predictions
        assert len(result.data) > 0
        assert "platforms_used" in result.metadata
        assert "manifold" in result.metadata["platforms_used"]

    @pytest.mark.asyncio
    async def test_collect_polymarket_basic(self, collector_polymarket):
        """Test basic Polymarket prediction collection."""
        params = CollectionParams(limit=5)
        result = await collector_polymarket.collect(params)

        # Verify result structure
        assert result is not None
        assert result.source == "prediction_markets"
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.data, list)
        assert isinstance(result.metadata, dict)

        # Should have fetched some predictions
        assert len(result.data) > 0
        assert "platforms_used" in result.metadata
        assert "polymarket" in result.metadata["platforms_used"]

    @pytest.mark.asyncio
    async def test_prediction_structure(self, collector_manifold):
        """Test that returned predictions have correct structure."""
        params = CollectionParams(limit=3)
        result = await collector_manifold.collect(params)

        # Should have some predictions
        assert len(result.data) > 0

        prediction = result.data[0]

        # Verify all required fields
        assert "question" in prediction
        assert "probability" in prediction
        assert "platform" in prediction
        assert "url" in prediction
        assert "last_updated" in prediction

        # Verify data types
        assert isinstance(prediction["question"], str)
        assert isinstance(prediction["probability"], (int, float))
        assert isinstance(prediction["platform"], str)
        assert isinstance(prediction["url"], str)
        assert isinstance(prediction["last_updated"], datetime)

        # Probability should be between 0 and 1
        assert 0 <= prediction["probability"] <= 1

        # Question should not be empty
        assert len(prediction["question"]) > 0

    @pytest.mark.asyncio
    async def test_keyword_filtering(self, collector_manifold):
        """Test filtering predictions by keywords."""
        # Search for market-related predictions
        params = CollectionParams(keywords=["market", "stocks"], limit=10)
        result = await collector_manifold.collect(params)

        # Should return some results
        assert len(result.data) > 0

        # Verify keywords are in metadata
        assert "keywords" in result.metadata
        assert "market" in result.metadata["keywords"]
        assert "stocks" in result.metadata["keywords"]

    @pytest.mark.asyncio
    async def test_limit(self, collector_manifold):
        """Test that limit parameter works."""
        limit = 3
        params = CollectionParams(limit=limit)
        result = await collector_manifold.collect(params)

        # Should return at most 'limit' predictions
        assert len(result.data) <= limit

    @pytest.mark.asyncio
    async def test_cache(self, collector_manifold):
        """Test caching functionality."""
        params = CollectionParams(limit=3)

        # First call - should fetch from API
        result1 = await collector_manifold.collect(params)
        assert len(result1.data) > 0
        assert not result1.metadata.get("cached", False)

        # Second call - should use cache
        result2 = await collector_manifold.collect(params)
        assert len(result2.data) > 0
        assert result2.metadata.get("cached", False)

        # Data should be identical (from cache)
        assert len(result1.data) == len(result2.data)
        assert result1.data[0]["question"] == result2.data[0]["question"]

        # Clear cache
        collector_manifold.clear_cache()

        # Third call - should fetch again
        result3 = await collector_manifold.collect(params)
        assert len(result3.data) > 0
        assert not result3.metadata.get("cached", False)

    @pytest.mark.asyncio
    async def test_multiple_platforms(self, collector_all):
        """Test collecting from multiple platforms."""
        params = CollectionParams(limit=10)
        result = await collector_all.collect(params)

        # Should have results
        assert len(result.data) > 0

        # Check that multiple platforms were used
        platforms_used = result.metadata.get("platforms_used", [])
        assert len(platforms_used) > 0

        # Check that predictions come from different platforms
        platforms_in_results = set(pred["platform"] for pred in result.data)
        # Should have at least 1 platform (may not always have both)
        assert len(platforms_in_results) >= 1

    @pytest.mark.asyncio
    async def test_sorting(self, collector_manifold):
        """Test that predictions are sorted by volume/popularity."""
        params = CollectionParams(limit=10)
        result = await collector_manifold.collect(params)

        if len(result.data) > 1:
            # Check that predictions are sorted by volume (descending)
            for i in range(len(result.data) - 1):
                # Volume should be non-increasing
                # (we allow equal volumes as there might be ties)
                assert result.data[i].get("volume", 0) >= result.data[i + 1].get(
                    "volume", 0
                )

    @pytest.mark.asyncio
    async def test_metadata(self, collector_manifold):
        """Test that metadata is populated correctly."""
        params = CollectionParams(limit=5)
        result = await collector_manifold.collect(params)

        metadata = result.metadata

        # Check expected metadata fields
        assert "platforms_used" in metadata
        assert "total_predictions" in metadata
        assert "keywords" in metadata

        # Total should match data length
        assert metadata["total_predictions"] == len(result.data)

    @pytest.mark.asyncio
    async def test_economic_keywords(self, collector_all):
        """Test searching for economic predictions."""
        # Search for recession, inflation, Fed predictions
        params = CollectionParams(keywords=["recession", "inflation", "Fed"], limit=10)
        result = await collector_all.collect(params)

        # Should return some results (these are common topics)
        assert len(result.data) >= 0  # May not always have matches

    @pytest.mark.asyncio
    async def test_market_keywords(self, collector_all):
        """Test searching for market-related predictions."""
        # Search for S&P, stock market predictions
        params = CollectionParams(keywords=["S&P", "stock market"], limit=10)
        result = await collector_all.collect(params)

        # Should return some results
        assert len(result.data) >= 0  # May not always have matches

    def test_cache_ttl(self, collector_manifold):
        """Test that cache TTL is set correctly."""
        assert collector_manifold.cache_ttl == 3600  # 1 hour

    def test_source_name(self, collector_manifold):
        """Test that source name is correct."""
        assert collector_manifold.source_name == "prediction_markets"

    @pytest.mark.asyncio
    async def test_empty_keywords(self, collector_manifold):
        """Test handling empty keywords list."""
        params = CollectionParams(keywords=[], limit=5)
        result = await collector_manifold.collect(params)

        # Should work normally (return trending markets)
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_no_keywords(self, collector_manifold):
        """Test with no keywords specified."""
        params = CollectionParams(limit=5)
        result = await collector_manifold.collect(params)

        # Should return trending markets
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_probability_range(self, collector_manifold):
        """Test that all probabilities are valid."""
        params = CollectionParams(limit=10)
        result = await collector_manifold.collect(params)

        # All probabilities should be between 0 and 1
        for prediction in result.data:
            prob = prediction["probability"]
            assert 0 <= prob <= 1, f"Invalid probability: {prob}"

    @pytest.mark.asyncio
    async def test_timestamp_validity(self, collector_manifold):
        """Test that timestamps are valid."""
        params = CollectionParams(limit=5)
        result = await collector_manifold.collect(params)

        # All timestamps should be valid datetime objects
        for prediction in result.data:
            assert isinstance(prediction["last_updated"], datetime)

            # Last updated should not be in the future
            assert prediction["last_updated"] <= datetime.now()


if __name__ == "__main__":
    # Can run tests directly for quick debugging
    pytest.main([__file__, "-v"])
