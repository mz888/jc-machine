"""SQLite database for storing market data and narratives."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class MarketSnapshotDB(Base):
    """Market snapshot database table."""

    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    snapshot_data = Column(Text, nullable=False)  # JSON serialized MarketSnapshot
    created_at = Column(DateTime, default=datetime.now)


class NewsHeadlineDB(Base):
    """News headline database table."""

    __tablename__ = "news_headlines"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(500))
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False)
    summary = Column(Text)
    keywords = Column(Text)  # JSON array
    created_at = Column(DateTime, default=datetime.now)


class DailyNarrativeDB(Base):
    """Daily narrative database table."""

    __tablename__ = "daily_narratives"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    headline = Column(String(200), nullable=False)
    narrative_data = Column(Text, nullable=False)  # JSON serialized DailyNarrative
    confidence_score = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class NarrativeDatabase:
    """Database manager for market narratives and data."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default: ./data/narratives.db)
        """
        if db_path is None:
            db_path = Path("./data/narratives.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create async engine
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}", echo=False, future=True
        )
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        logger.info(f"Database initialized at {self.db_path}")

    async def create_tables(self):
        """Create database tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def save_market_snapshot(self, snapshot, date: datetime) -> int:
        """
        Save market snapshot to database.

        Args:
            snapshot: MarketSnapshot object
            date: Date of the snapshot

        Returns:
            ID of inserted record
        """
        from src.storage.models import MarketSnapshot

        # Convert to JSON
        if isinstance(snapshot, MarketSnapshot):
            snapshot_json = snapshot.model_dump_json()
        else:
            snapshot_json = json.dumps(snapshot, default=str)

        async with self.async_session() as session:
            # Check if snapshot for this date exists
            stmt = select(MarketSnapshotDB.id).where(MarketSnapshotDB.date == date)
            result = await session.execute(stmt)
            existing_id = result.scalar()

            if existing_id:
                # Update existing
                await session.execute(
                    text("UPDATE market_snapshots SET snapshot_data = :data WHERE id = :id"),
                    {"data": snapshot_json, "id": existing_id},
                )
                await session.commit()
                logger.info(f"Updated market snapshot for {date.date()}")
                return existing_id
            else:
                # Insert new
                snapshot_db = MarketSnapshotDB(date=date, snapshot_data=snapshot_json)
                session.add(snapshot_db)
                await session.commit()
                logger.info(f"Saved market snapshot for {date.date()}")
                return snapshot_db.id

    async def save_news_headlines(self, headlines: List, date: datetime) -> int:
        """
        Save news headlines to database.

        Args:
            headlines: List of NewsArticle objects
            date: Date for the headlines

        Returns:
            Number of headlines saved
        """
        from src.storage.models import NewsArticle

        async with self.async_session() as session:
            count = 0
            for article in headlines:
                if isinstance(article, NewsArticle):
                    headline_db = NewsHeadlineDB(
                        date=date,
                        title=article.title,
                        url=article.url,
                        source=article.source,
                        published_at=article.published_at,
                        summary=article.summary,
                        keywords=json.dumps(article.keywords),
                    )
                    session.add(headline_db)
                    count += 1

            await session.commit()
            logger.info(f"Saved {count} news headlines for {date.date()}")
            return count

    async def save_daily_narrative(self, narrative, date: datetime) -> int:
        """
        Save daily narrative to database.

        Args:
            narrative: DailyNarrative object
            date: Date of the narrative

        Returns:
            ID of inserted record
        """
        from src.storage.models import DailyNarrative

        # Convert to JSON
        if isinstance(narrative, DailyNarrative):
            narrative_json = narrative.model_dump_json()
            headline = narrative.headline
            confidence = narrative.confidence_score
        else:
            narrative_json = json.dumps(narrative, default=str)
            headline = narrative.get("headline", "Unknown")
            confidence = narrative.get("confidence_score", 0.0)

        async with self.async_session() as session:
            # Check if narrative for this date exists
            stmt = select(DailyNarrativeDB.id).where(DailyNarrativeDB.date == date)
            result = await session.execute(stmt)
            existing_id = result.scalar()

            if existing_id:
                # Update existing
                await session.execute(
                    text("""UPDATE daily_narratives
                       SET headline = :headline, narrative_data = :data,
                           confidence_score = :confidence
                       WHERE id = :id"""),
                    {
                        "headline": headline,
                        "data": narrative_json,
                        "confidence": confidence,
                        "id": existing_id,
                    },
                )
                await session.commit()
                logger.info(f"Updated daily narrative for {date.date()}")
                return existing_id
            else:
                # Insert new
                narrative_db = DailyNarrativeDB(
                    date=date,
                    headline=headline,
                    narrative_data=narrative_json,
                    confidence_score=confidence,
                )
                session.add(narrative_db)
                await session.commit()
                logger.info(f"Saved daily narrative for {date.date()}")
                return narrative_db.id

    async def get_market_snapshot(self, date: datetime):
        """
        Retrieve market snapshot for a date.

        Args:
            date: Date to retrieve

        Returns:
            MarketSnapshot object or None
        """
        from src.storage.models import MarketSnapshot

        async with self.async_session() as session:
            stmt = select(MarketSnapshotDB.snapshot_data).where(MarketSnapshotDB.date == date)
            result = await session.execute(stmt)
            snapshot_json = result.scalar()

            if snapshot_json:
                return MarketSnapshot.model_validate_json(snapshot_json)
            return None

    async def get_daily_narrative(self, date: datetime):
        """
        Retrieve daily narrative for a date.

        Args:
            date: Date to retrieve

        Returns:
            DailyNarrative object or None
        """
        from src.storage.models import DailyNarrative

        async with self.async_session() as session:
            stmt = select(DailyNarrativeDB.narrative_data).where(DailyNarrativeDB.date == date)
            result = await session.execute(stmt)
            narrative_json = result.scalar()

            if narrative_json:
                return DailyNarrative.model_validate_json(narrative_json)
            return None

    async def get_recent_narratives(self, limit: int = 10) -> List:
        """
        Get recent narratives.

        Args:
            limit: Maximum number of narratives to return

        Returns:
            List of DailyNarrative objects
        """
        from src.storage.models import DailyNarrative

        async with self.async_session() as session:
            stmt = select(DailyNarrativeDB.narrative_data).order_by(
                DailyNarrativeDB.date.desc()
            ).limit(limit)
            result = await session.execute(stmt)
            narratives = []
            for row in result:
                narrative_json = row[0]
                narratives.append(DailyNarrative.model_validate_json(narrative_json))
            return narratives

    async def close(self):
        """Close database connection."""
        await self.engine.dispose()
        logger.info("Database connection closed")
