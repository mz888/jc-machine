"""News data collector using RSS feeds and NewsAPI."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import feedparser
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.collectors.base import CollectionParams, CollectionResult, DataCollector


# Default RSS feeds for financial news
# Note: Some feeds (Reuters, Yahoo) were removed due to parse errors
DEFAULT_RSS_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # CNBC Top News
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",  # CNBC Business
    "https://www.cnbc.com/id/15839135/device/rss/rss.html",  # CNBC Markets
    "https://www.ft.com/rss/home",  # Financial Times
    "https://feeds.bloomberg.com/markets/news.rss",  # Bloomberg Markets (may require validation)
]


class NewsCollector(DataCollector):
    """Collects news from RSS feeds and optionally NewsAPI."""

    def __init__(
        self,
        newsapi_key: Optional[str] = None,
        rss_feeds: Optional[List[str]] = None,
        cache_enabled: bool = True,
    ):
        """
        Initialize news collector.

        Args:
            newsapi_key: Optional NewsAPI key (100 calls/day free)
            rss_feeds: Optional list of RSS feed URLs (uses defaults if None)
            cache_enabled: Whether to enable caching
        """
        super().__init__(cache_enabled)
        self.newsapi_key = newsapi_key
        self.rss_feeds = rss_feeds or DEFAULT_RSS_FEEDS
        # Two-level cache:
        #   _rss_cache  – keyed by date only; stores all raw RSS articles before
        #                 keyword filtering.  Re-used across search_news calls with
        #                 different keywords so RSS endpoints are only hit once.
        #   _cache      – keyed by date + keywords; stores the final filtered result.
        self._rss_cache: Dict[str, List[Dict]] = {}
        self._cache: Dict[str, List[Dict]] = {}

    @property
    def cache_ttl(self) -> int:
        """Cache TTL in seconds (1 hour)."""
        return 3600

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "news_aggregator"

    def _parse_rss_feed(self, feed_url: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Parse a single RSS feed.

        Args:
            feed_url: RSS feed URL
            limit: Maximum number of articles to return

        Returns:
            List of article dicts
        """
        try:
            logger.debug(f"Fetching RSS feed: {feed_url}")
            feed = feedparser.parse(feed_url)

            if feed.bozo:  # Parsing error
                logger.warning(f"RSS feed parsing error for {feed_url}: {feed.bozo_exception}")
                return []

            articles = []
            for entry in feed.entries[:limit] if limit else feed.entries:
                # Extract date - different feeds use different fields
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    from time import mktime

                    published = datetime.fromtimestamp(mktime(entry.published_parsed))
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    from time import mktime

                    published = datetime.fromtimestamp(mktime(entry.updated_parsed))
                else:
                    published = datetime.now()

                # Extract summary/description
                summary = None
                if hasattr(entry, "summary"):
                    summary = entry.summary
                elif hasattr(entry, "description"):
                    summary = entry.description

                article = {
                    "title": entry.get("title", "No title"),
                    "url": entry.get("link"),
                    "source": feed.feed.get("title", feed_url),
                    "published_at": published,
                    "summary": summary,
                    "keywords": [],  # RSS feeds don't typically have keywords
                }
                articles.append(article)

            logger.debug(f"Fetched {len(articles)} articles from {feed_url}")
            return articles

        except Exception as e:
            logger.error(f"Error parsing RSS feed {feed_url}: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch_newsapi(
        self,
        keywords: Optional[List[str]] = None,
        from_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Fetch news from NewsAPI.

        Args:
            keywords: Keywords to search for
            from_date: Fetch articles from this date onwards
            limit: Maximum number of articles

        Returns:
            List of article dicts
        """
        if not self.newsapi_key:
            logger.debug("NewsAPI key not provided, skipping NewsAPI")
            return []

        try:
            # Build query
            query = " OR ".join(keywords) if keywords else "market OR stocks OR economy"
            from_param = (from_date or datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            url = "https://newsapi.org/v2/everything"
            params = {
                "q": query,
                "from": from_param,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": min(limit, 100),  # NewsAPI max is 100
                "apiKey": self.newsapi_key,
            }

            logger.debug(f"Fetching from NewsAPI with query: {query}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            if data.get("status") != "ok":
                logger.warning(f"NewsAPI returned non-ok status: {data.get('message')}")
                return []

            articles = []
            for item in data.get("articles", []):
                article = {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "published_at": datetime.fromisoformat(
                        item.get("publishedAt", "").replace("Z", "+00:00")
                    ),
                    "summary": item.get("description"),
                    "keywords": keywords or [],
                }
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from NewsAPI")
            return articles

        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []

    def _filter_by_keywords(
        self, articles: List[Dict], keywords: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Filter articles by keywords in title or summary.

        Args:
            articles: List of articles
            keywords: Keywords to filter by

        Returns:
            Filtered articles
        """
        if not keywords:
            return articles

        filtered = []
        keywords_lower = [k.lower() for k in keywords]

        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)

        return filtered

    async def collect(self, params: CollectionParams) -> CollectionResult:
        """
        Collect news articles from RSS feeds and NewsAPI.

        Args:
            params: Collection parameters with optional keywords, date, and limit

        Returns:
            CollectionResult with news articles
        """
        logger.info("Collecting news articles")

        date_key = params.date.strftime("%Y-%m-%d") if params.date else "latest"
        keywords_key = ",".join(sorted(params.keywords or []))
        cache_key = f"news_{date_key}_{keywords_key}"

        # Check final-result cache (date + keywords)
        if self.cache_enabled and cache_key in self._cache:
            logger.debug("Using cached news data")
            return CollectionResult(
                data=self._cache[cache_key],
                timestamp=datetime.now(),
                source=self.source_name,
                metadata={"cached": True},
            )

        sources_used = []

        # --- Level 1: raw RSS cache (keyed by date only) ---
        rss_cache_key = f"rss_{date_key}"
        if self.cache_enabled and rss_cache_key in self._rss_cache:
            logger.debug("Using cached raw RSS articles")
            rss_articles = self._rss_cache[rss_cache_key]
            sources_used.extend(f"RSS: {url}" for url in self.rss_feeds)
        else:
            rss_articles = []
            for feed_url in self.rss_feeds:
                articles = self._parse_rss_feed(feed_url)
                rss_articles.extend(articles)
                if articles:
                    sources_used.append(f"RSS: {feed_url}")
            if self.cache_enabled:
                self._rss_cache[rss_cache_key] = rss_articles

        all_articles = list(rss_articles)

        # Fetch from NewsAPI if key available (still per-keyword; API returns different results)
        if self.newsapi_key:
            newsapi_articles = await self._fetch_newsapi(
                keywords=params.keywords,
                from_date=params.date,
                limit=params.limit or 50,
            )
            all_articles.extend(newsapi_articles)
            if newsapi_articles:
                sources_used.append("NewsAPI")

        # Filter by keywords if provided
        if params.keywords:
            all_articles = self._filter_by_keywords(all_articles, params.keywords)

        # Remove duplicates based on title (case-insensitive)
        seen_titles = set()
        unique_articles = []
        for article in all_articles:
            title_lower = article["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)

        # Sort by published date (most recent first)
        # Normalize timezone-aware datetimes to UTC and naive datetimes to UTC
        def get_sortable_datetime(article):
            dt = article["published_at"]
            if dt.tzinfo is not None:
                # Convert to UTC and make naive
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt

        unique_articles.sort(key=get_sortable_datetime, reverse=True)

        # Apply limit if specified
        if params.limit:
            unique_articles = unique_articles[: params.limit]

        # Cache results
        if self.cache_enabled:
            self._cache[cache_key] = unique_articles

        logger.info(
            f"Collected {len(unique_articles)} unique articles from {len(sources_used)} sources"
        )

        return CollectionResult(
            data=unique_articles,
            timestamp=datetime.now(),
            source=self.source_name,
            metadata={
                "sources_used": sources_used,
                "total_articles": len(all_articles),
                "unique_articles": len(unique_articles),
                "keywords_used": params.keywords or [],
            },
        )

    def clear_cache(self):
        """Clear the internal cache (both levels)."""
        self._cache.clear()
        self._rss_cache.clear()
        logger.debug("News collector cache cleared")
