"""Agent controller for market narrative generation.

This module orchestrates the entire agent workflow using LangGraph.
"""

import os
from datetime import datetime
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from loguru import logger

from src.agent.graph import create_agent_graph
from src.agent.state import AgentState, create_initial_state
from src.agent.tools import initialize_tools
from src.analysis.processor import DataProcessor
from src.collectors.news import NewsCollector
from src.collectors.prediction import PredictionCollector
from src.collectors.price import PriceCollector
from src.config import Config
from src.storage.models import DailyNarrative


class AgentController:
    """Controller for the market narrative agent.

    This class:
    1. Initializes all collectors and tools
    2. Creates the LangGraph workflow
    3. Executes the 4-phase analysis
    4. Returns the final narrative
    """

    def __init__(self, config: Config):
        """Initialize the agent controller.

        Args:
            config: Application configuration
        """
        self.config = config
        logger.info("Initializing AgentController")

        # Initialize collectors
        self.price_collector = PriceCollector(cache_enabled=True)
        self.news_collector = NewsCollector(
            newsapi_key=os.getenv("NEWSAPI_KEY"), cache_enabled=True
        )
        self.prediction_collector = PredictionCollector(
            platforms=["manifold", "polymarket"], cache_enabled=True
        )

        # Initialize data processor
        self.data_processor = DataProcessor(self.config.processing)

        # Initialize tools
        initialize_tools(
            price_collector=self.price_collector,
            news_collector=self.news_collector,
            prediction_collector=self.prediction_collector,
            data_processor=self.data_processor,
            config=self.config,
        )

        # Initialize LLM
        self.llm = self._create_llm()

        # Create LangGraph workflow
        self.graph = create_agent_graph(self.llm)

        logger.info("AgentController initialized successfully")

    def _create_llm(self):
        """Create LLM instance based on config."""
        provider = self.config.llm.provider.lower()
        model = self.config.primary_model
        temperature = self.config.llm.temperature

        logger.info(f"Creating LLM: provider={provider}, model={model}")

        if provider == "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=self.config.llm.max_tokens,
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=self.config.llm.max_tokens,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    async def generate_narrative(
        self, date: Optional[datetime] = None
    ) -> DailyNarrative:
        """Generate a market narrative for the given date.

        This is the main entry point that executes the full 4-phase workflow.

        Args:
            date: Date to analyze. Defaults to today.

        Returns:
            DailyNarrative with the final analysis
        """
        analysis_date = date or datetime.now()
        logger.info(f"Starting narrative generation for {analysis_date.date()}")

        # Create initial state
        initial_state = create_initial_state(date=analysis_date)

        try:
            # Execute the LangGraph workflow
            logger.info("Executing LangGraph workflow...")
            final_state = await self.graph.ainvoke(initial_state)

            # Store last state for orchestrator access
            self.last_state = final_state

            # Convert final state to DailyNarrative
            narrative = self._state_to_narrative(final_state)

            logger.info("Narrative generation complete")
            return narrative

        except Exception as e:
            logger.error(f"Error during narrative generation: {e}")
            raise

    def _state_to_narrative(self, state: AgentState) -> DailyNarrative:
        """Convert final agent state to DailyNarrative model.

        Args:
            state: Final agent state after synthesis

        Returns:
            DailyNarrative for output/storage
        """
        # Convert key_moves_explained from Dict[str, str] to List[dict]
        key_moves_list = [
            {"symbol": symbol, "explanation": explanation}
            for symbol, explanation in state["key_moves_explained"].items()
        ]

        # Convert prediction_insights from List[str] to List[dict] if needed
        prediction_insights_list = []
        for insight in state["prediction_insights"]:
            if isinstance(insight, dict):
                prediction_insights_list.append(insight)
            else:
                prediction_insights_list.append({"insight": insight})

        return DailyNarrative(
            date=state["date"],
            headline=state["headline"] or f"Market Analysis for {state['date'].strftime('%Y-%m-%d')}",
            primary_narrative=state["primary_narrative"],
            supporting_narratives=state["supporting_narratives"],
            key_moves_explained=key_moves_list,
            prediction_market_insights=prediction_insights_list,
            unexplained_moves=state["unexplained_moves"],
            looking_ahead=state["looking_ahead"],
            confidence_score=state["confidence_score"],
            data_sources=self._get_data_sources(state),
            metadata={
                "tools_used": state["tools_used"],
                "num_hypotheses": len(state["hypotheses"]),
                "num_investigations": len(state["investigation_results"]),
            },
        )

    def _generate_headline(self, state: AgentState) -> str:
        """Generate a headline from the primary narrative.

        Args:
            state: Final agent state

        Returns:
            Short headline string
        """
        # Simple implementation: Take first sentence or truncate
        narrative = state["primary_narrative"]
        if not narrative:
            return f"Market Analysis for {state['date'].strftime('%Y-%m-%d')}"

        # Take first sentence or first 80 characters
        first_sentence = narrative.split(".")[0]
        if len(first_sentence) <= 80:
            return first_sentence
        return first_sentence[:77] + "..."

    def _get_data_sources(self, state: AgentState) -> list[str]:
        """Extract data sources used from state.

        Args:
            state: Final agent state

        Returns:
            List of data source names
        """
        sources = set()

        if state["market_snapshot"]:
            sources.add("yfinance")

        if state["news_headlines"]:
            sources.add("RSS feeds")
            # Check if NewsAPI was used (would be in metadata)

        if state["additional_data"].get("predictions"):
            sources.add("Manifold Markets")
            sources.add("Polymarket")

        return sorted(list(sources))

    async def test_workflow(self) -> None:
        """Test the workflow with placeholder data.

        Useful for debugging and development.
        """
        logger.info("Running test workflow...")

        state = create_initial_state()
        final_state = await self.graph.ainvoke(state)

        logger.info("Test workflow complete!")
        logger.info(f"Final phase: {final_state['current_phase']}")
        logger.info(f"Primary narrative: {final_state['primary_narrative']}")
        logger.info(f"Confidence: {final_state['confidence_score']}")
