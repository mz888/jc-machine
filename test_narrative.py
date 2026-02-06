"""Test script to generate and display a market narrative."""

import asyncio
import json
from datetime import datetime

from loguru import logger

from src.config import load_config
from src.agent.controller import AgentController


async def main():
    """Generate and display a market narrative."""
    # Disable debug logging for cleaner output
    logger.remove()
    logger.add(lambda msg: None, level="WARNING")  # Suppress most logs

    print("=" * 80)
    print("MARKET NARRATIVE AGENT - Live Test")
    print("=" * 80)
    print()

    # Load configuration
    config = load_config()

    # Create agent controller
    print("Initializing agent...")
    controller = AgentController(config)

    # Generate narrative
    print("Generating narrative for today...")
    print()
    narrative = await controller.generate_narrative()

    # Display results
    print("=" * 80)
    print(f"MARKET NARRATIVE FOR {narrative.date.strftime('%Y-%m-%d')}")
    print("=" * 80)
    print()

    print("HEADLINE:")
    print(f"  {narrative.headline}")
    print()

    print("PRIMARY NARRATIVE:")
    print(f"  {narrative.primary_narrative}")
    print()

    if narrative.supporting_narratives:
        print("SUPPORTING POINTS:")
        for i, point in enumerate(narrative.supporting_narratives, 1):
            print(f"  {i}. {point}")
        print()

    if narrative.key_moves_explained:
        print("KEY MOVES EXPLAINED:")
        for move in narrative.key_moves_explained:
            print(f"  • {move.get('symbol', 'Unknown')}: {move.get('explanation', 'N/A')}")
        print()

    if narrative.unexplained_moves:
        print("UNEXPLAINED MOVES:")
        for move in narrative.unexplained_moves:
            print(f"  • {move}")
        print()

    if narrative.looking_ahead:
        print("LOOKING AHEAD:")
        print(f"  {narrative.looking_ahead}")
        print()

    print("=" * 80)
    print(f"Confidence Score: {narrative.confidence_score:.2f}")
    print(f"Data Sources: {', '.join(narrative.data_sources)}")
    print(f"Tools Used: {narrative.metadata.get('tools_used', [])}")
    print(f"Hypotheses Generated: {narrative.metadata.get('num_hypotheses', 0)}")
    print(f"Investigations Conducted: {narrative.metadata.get('num_investigations', 0)}")
    print("=" * 80)

    # Save to file
    output_file = f"narrative_{narrative.date.strftime('%Y-%m-%d')}.json"
    with open(output_file, "w") as f:
        json.dump(narrative.model_dump(mode="json"), f, indent=2, default=str)
    print(f"\nNarrative saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
