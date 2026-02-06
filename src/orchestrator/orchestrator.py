"""Orchestrator for daily narrative generation."""

from datetime import datetime
from typing import Optional

from loguru import logger

from src.agent.controller import AgentController
from src.config import Config
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

        try:
            # Run the agent workflow
            narrative = await self.agent_controller.generate_narrative(date)

            logger.info(f"Narrative generated successfully: {narrative.headline}")
            logger.info(f"Confidence score: {narrative.confidence_score}")

            return narrative

        except Exception as e:
            logger.error(f"Error during narrative generation: {e}")
            raise
