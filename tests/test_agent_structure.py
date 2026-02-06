"""Tests for agent structure and workflow."""

import pytest
from datetime import datetime

from src.agent.controller import AgentController
from src.agent.state import AgentState, create_initial_state
from src.config import load_config


class TestAgentStructure:
    """Test suite for agent structure."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return load_config("config.yaml")

    def test_create_initial_state(self):
        """Test creating initial agent state."""
        state = create_initial_state()

        assert state["current_phase"] == "observation"
        assert isinstance(state["date"], datetime)
        assert state["market_snapshot"] is None
        assert len(state["news_headlines"]) == 0
        assert len(state["hypotheses"]) == 0
        assert state["primary_narrative"] == ""
        assert state["confidence_score"] == 0.0
        assert len(state["tools_used"]) == 0

    def test_create_initial_state_with_date(self):
        """Test creating initial state with specific date."""
        test_date = datetime(2024, 1, 1, 12, 0, 0)
        state = create_initial_state(date=test_date)

        assert state["date"] == test_date

    def test_agent_controller_init(self, config):
        """Test AgentController initialization."""
        controller = AgentController(config)

        assert controller.config == config
        assert controller.price_collector is not None
        assert controller.news_collector is not None
        assert controller.prediction_collector is not None
        assert controller.data_processor is not None
        assert controller.llm is not None
        assert controller.graph is not None

    @pytest.mark.asyncio
    async def test_agent_workflow_structure(self, config):
        """Test that agent workflow runs through all phases."""
        controller = AgentController(config)

        # Run test workflow with placeholder data
        await controller.test_workflow()

        # If we get here without errors, the structure is sound


if __name__ == "__main__":
    # Can run tests directly for quick debugging
    pytest.main([__file__, "-v"])
