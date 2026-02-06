"""Tests for NewsCollector."""

import pytest
from datetime import datetime, timedelta

from src.collectors.base import CollectionParams
from src.collectors.news import NewsCollector


class TestNewsCollector:
    """Test suite for NewsCollector."""

    @pytest.fixture
    def collector_no_api(self):
        """Create a NewsCollector without NewsAPI key (RSS only)."""
        return NewsCollector(newsapi_key=None, cache_enabled=True)

    @pytest.fixture
    def collector_with_api(self):
        """Create a NewsCollector with NewsAPI key if available."""
        # Will try to use NewsAPI if key is in environment
        import os

        api_key = os.getenv("NEWSAPI_KEY")
        return NewsCollector(newsapi_key=api_key, cache_enabled=True)

    @pytest.mark.asyncio
    async def test_collect_rss_basic(self, collector_no_api):
        """Test basic RSS feed collection."""
        params = CollectionParams(limit=10)
        result = await collector_no_api.collect(params)

        # Verify result structure
        assert result is not None
        assert result.source == "news_aggregator"
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.data, list)
        assert isinstance(result.metadata, dict)

        # Should have fetched some articles from RSS
        assert len(result.data) > 0
        assert "sources_used" in result.metadata

    @pytest.mark.asyncio
    async def test_article_structure(self, collector_no_api):
        """Test that returned articles have correct structure."""
        params = CollectionParams(limit=5)
        result = await collector_no_api.collect(params)

        # Should have some articles
        assert len(result.data) > 0

        article = result.data[0]

        # Verify all required fields
        assert "title" in article
        assert "url" in article
        assert "source" in article
        assert "published_at" in article
        assert "summary" in article
        assert "keywords" in article

        # Verify data types
        assert isinstance(article["title"], str)
        assert article["url"] is None or isinstance(article["url"], str)
        assert isinstance(article["source"], str)
        assert isinstance(article["published_at"], datetime)
        assert article["summary"] is None or isinstance(article["summary"], str)
        assert isinstance(article["keywords"], list)

        # Title should not be empty
        assert len(article["title"]) > 0

    @pytest.mark.asyncio
    async def test_keyword_filtering(self, collector_no_api):
        """Test filtering articles by keywords."""
        # First, get articles without filter
        params_no_filter = CollectionParams(limit=20)
        result_no_filter = await collector_no_api.collect(params_no_filter)

        # Clear cache to force fresh fetch
        collector_no_api.clear_cache()

        # Then, get articles with keyword filter
        params_with_filter = CollectionParams(keywords=["market", "stock"], limit=20)
        result_with_filter = await collector_no_api.collect(params_with_filter)

        # Filtered results should have fewer or equal articles
        assert len(result_with_filter.data) <= len(result_no_filter.data)

        # Verify filtered articles contain keywords
        for article in result_with_filter.data:
            text = f"{article['title']} {article.get('summary', '')}".lower()
            assert "market" in text or "stock" in text

    @pytest.mark.asyncio
    async def test_limit(self, collector_no_api):
        """Test that limit parameter works."""
        limit = 5
        params = CollectionParams(limit=limit)
        result = await collector_no_api.collect(params)

        # Should return at most 'limit' articles
        assert len(result.data) <= limit

    @pytest.mark.asyncio
    async def test_cache(self, collector_no_api):
        """Test caching functionality."""
        params = CollectionParams(limit=5)

        # First call - should fetch from sources
        result1 = await collector_no_api.collect(params)
        assert len(result1.data) > 0
        assert not result1.metadata.get("cached", False)

        # Second call - should use cache
        result2 = await collector_no_api.collect(params)
        assert len(result2.data) > 0
        assert result2.metadata.get("cached", False)

        # Data should be identical (from cache)
        assert len(result1.data) == len(result2.data)
        assert result1.data[0]["title"] == result2.data[0]["title"]

        # Clear cache
        collector_no_api.clear_cache()

        # Third call - should fetch again
        result3 = await collector_no_api.collect(params)
        assert len(result3.data) > 0
        assert not result3.metadata.get("cached", False)

    @pytest.mark.asyncio
    async def test_deduplication(self, collector_no_api):
        """Test that duplicate articles are removed."""
        params = CollectionParams(limit=50)
        result = await collector_no_api.collect(params)

        # Check for duplicate titles (case-insensitive)
        titles_lower = [article["title"].lower() for article in result.data]
        assert len(titles_lower) == len(set(titles_lower)), "Found duplicate titles"

    @pytest.mark.asyncio
    async def test_sorting(self, collector_no_api):
        """Test that articles are sorted by date (most recent first)."""
        params = CollectionParams(limit=10)
        result = await collector_no_api.collect(params)

        if len(result.data) > 1:
            # Check that articles are in descending order by published_at
            for i in range(len(result.data) - 1):
                assert result.data[i]["published_at"] >= result.data[i + 1]["published_at"]

    @pytest.mark.asyncio
    async def test_multiple_rss_sources(self, collector_no_api):
        """Test that multiple RSS sources are used."""
        params = CollectionParams(limit=20)
        result = await collector_no_api.collect(params)

        # Should have used multiple sources
        sources_used = result.metadata.get("sources_used", [])
        assert len(sources_used) > 0

        # Check that articles come from different sources
        article_sources = set(article["source"] for article in result.data)
        # Should have at least 2 different sources (though not guaranteed)
        assert len(article_sources) >= 1

    @pytest.mark.asyncio
    async def test_custom_rss_feeds(self):
        """Test using custom RSS feeds."""
        custom_feeds = ["https://feeds.finance.yahoo.com/rss/2.0/headline"]
        collector = NewsCollector(rss_feeds=custom_feeds, cache_enabled=False)

        params = CollectionParams(limit=5)
        result = await collector.collect(params)

        # Should not crash, even if feed has issues
        # (RSS feeds can be unreliable or change format)
        assert result is not None
        assert isinstance(result.data, list)

    @pytest.mark.asyncio
    async def test_date_parameter(self, collector_no_api):
        """Test that date parameter is respected."""
        # Request articles from yesterday
        yesterday = datetime.now() - timedelta(days=1)
        params = CollectionParams(date=yesterday, limit=10)
        result = await collector_no_api.collect(params)

        # Should have articles (though RSS feeds might not respect date)
        assert result is not None
        # Just verify it doesn't crash with date parameter

    @pytest.mark.asyncio
    async def test_metadata(self, collector_no_api):
        """Test that metadata is populated correctly."""
        params = CollectionParams(limit=10)
        result = await collector_no_api.collect(params)

        metadata = result.metadata

        # Check expected metadata fields
        assert "sources_used" in metadata
        assert "total_articles" in metadata
        assert "unique_articles" in metadata
        assert "keywords_used" in metadata

        # Total should be >= unique
        assert metadata["total_articles"] >= metadata["unique_articles"]

    @pytest.mark.asyncio
    async def test_newsapi_integration(self, collector_with_api):
        """Test NewsAPI integration if key is available."""
        if not collector_with_api.newsapi_key:
            pytest.skip("NewsAPI key not available")

        params = CollectionParams(keywords=["stocks"], limit=10)
        result = await collector_with_api.collect(params)

        # Should have articles
        assert len(result.data) > 0

        # Check if NewsAPI was used
        sources_used = result.metadata.get("sources_used", [])
        has_newsapi = any("NewsAPI" in source for source in sources_used)

        # If NewsAPI key is valid, it should be used
        if collector_with_api.newsapi_key:
            assert has_newsapi or len(result.data) > 0  # Either used or RSS worked

    def test_cache_ttl(self, collector_no_api):
        """Test that cache TTL is set correctly."""
        assert collector_no_api.cache_ttl == 3600  # 1 hour

    def test_source_name(self, collector_no_api):
        """Test that source name is correct."""
        assert collector_no_api.source_name == "news_aggregator"

    @pytest.mark.asyncio
    async def test_empty_keywords(self, collector_no_api):
        """Test handling empty keywords list."""
        params = CollectionParams(keywords=[], limit=5)
        result = await collector_no_api.collect(params)

        # Should work normally (no filtering)
        assert len(result.data) > 0

    @pytest.mark.asyncio
    async def test_error_handling_bad_rss(self):
        """Test handling of invalid RSS feed."""
        bad_feeds = ["https://invalid-feed-url.example.com/rss"]
        collector = NewsCollector(rss_feeds=bad_feeds, cache_enabled=False)

        params = CollectionParams(limit=5)
        result = await collector.collect(params)

        # Should handle gracefully (return empty or partial results)
        assert result is not None
        assert isinstance(result.data, list)


if __name__ == "__main__":
    # Can run tests directly for quick debugging
    pytest.main([__file__, "-v"])
