"""Orchestrator for daily narrative generation."""

import io
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from src.agent.controller import AgentController
from src.config import Config
from src.output.formatter import OutputWriter
from src.storage.database import NarrativeDatabase
from src.storage.models import DailyNarrative


class Orchestrator:
    """Orchestrates the daily narrative generation process."""

    def __init__(self, config: Config):
        """
        Initialize orchestrator.

        Args:
            config: Application configuration
        """
        self.config = config
        logger.info("Orchestrator initializing...")

        # Initialize agent controller
        self.agent_controller = AgentController(config)

        # Initialize output writer
        self.output_writer = OutputWriter(Path("./outputs"))

        # Initialize database
        self.database = NarrativeDatabase(Path("./data/narratives.db"))

        logger.info("Orchestrator initialized successfully")

    async def run_daily(self, date: Optional[datetime] = None) -> DailyNarrative:
        """
        Run daily narrative generation using the 4-phase agent workflow.

        Args:
            date: Date to generate narrative for (defaults to today)

        Returns:
            Generated DailyNarrative
        """
        if date is None:
            date = datetime.now()

        logger.info(f"Starting daily narrative generation for {date.date()}")

        # Initialize database tables
        await self.database.create_tables()

        # Set up log capture
        log_stream = io.StringIO()
        log_id = logger.add(log_stream, format="{time} | {level} | {message}")

        try:
            # Run the agent workflow
            narrative = await self.agent_controller.generate_narrative(date)

            logger.info(f"Narrative generated successfully: {narrative.headline}")
            logger.info(f"Confidence score: {narrative.confidence_score}")

            # Get market snapshot from agent state for output formatting
            market_snapshot = None
            if hasattr(self.agent_controller, "last_state"):
                # Try to get market_snapshot (MarketSnapshot object)
                market_snapshot = self.agent_controller.last_state.get("market_snapshot")

                # If not found, try to get market_data_dict from additional_data
                if not market_snapshot:
                    additional_data = self.agent_controller.last_state.get("additional_data", {})
                    market_data_dict = additional_data.get("market_data_dict")
                    if market_data_dict:
                        logger.info("Retrieved market_data_dict from additional_data")
                        logger.info(
                            f"Market data: "
                            f"{len(market_data_dict.get('biggest_gainers', []))} gainers, "
                            f"{len(market_data_dict.get('biggest_losers', []))} losers, "
                            f"{len(market_data_dict.get('sector_performance', {}))} sectors"
                        )
                        # Store the dict - formatter will handle it
                        market_snapshot = market_data_dict
                    else:
                        logger.warning("No market data found - table will not be displayed in markdown")
                else:
                    logger.info(
                        f"Market snapshot retrieved: "
                        f"{len(market_snapshot.biggest_gainers)} gainers, "
                        f"{len(market_snapshot.biggest_losers)} losers, "
                        f"{len(market_snapshot.sector_performance)} sectors"
                    )

            # Save outputs to files
            logger.info("Saving outputs to files...")
            log_content = log_stream.getvalue()  # Get logs before removing handler
            output_files = self.output_writer.save_narrative(
                narrative=narrative, market_snapshot=market_snapshot, logs=log_content
            )
            logger.info(f"Saved {len(output_files)} output files")

            # Note: Market snapshot is already saved by save_narrative above
            # No need to save it again as a separate raw data file

            # Save to database
            logger.info("Saving to database...")
            await self.database.save_daily_narrative(narrative, date)

            if market_snapshot:
                await self.database.save_market_snapshot(market_snapshot, date)

            # Save headlines if available
            if hasattr(self.agent_controller, "last_state"):
                news_headlines = self.agent_controller.last_state.get("news_headlines", [])
                if news_headlines:
                    await self.database.save_news_headlines(news_headlines, date)

            logger.info("All data saved successfully")

            return narrative

        except Exception as e:
            logger.error(f"Error during narrative generation: {e}")
            raise
        finally:
            # Always remove the log handler
            logger.remove(log_id)
