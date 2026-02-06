"""Main entry point for the Market Narrative Agent."""

import asyncio
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import load_config
from src.orchestrator.orchestrator import Orchestrator


async def main():
    """Run the market narrative agent."""
    logger.info("Starting Market Narrative Agent")

    # Load configuration
    config = load_config()

    # Create orchestrator
    orchestrator = Orchestrator(config)

    # Run daily narrative generation
    narrative = await orchestrator.run_daily()

    logger.info(f"Narrative generated successfully: {narrative.headline}")

    return narrative


if __name__ == "__main__":
    asyncio.run(main())
