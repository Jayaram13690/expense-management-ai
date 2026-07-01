"""
Test suite for ExpenseAgent.

This module validates the ExpenseAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.expense_agent import ExpenseAgent
from prompts.expense_prompt import EXPENSE_AGENT_SYSTEM_PROMPT
from tools.expense_tools import get_claim, preview_claim, submit_claim


class TestExpenseAgentInitialization:
    """Test ExpenseAgent initialization and inheritance."""

    def test_inherits_from_base_agent(self):
        """Test that ExpenseAgent inherits from BaseAgent."""
        with patch("agents.base_agent.StrandsAgent"):
            agent = ExpenseAgent()
            assert isinstance(agent, ExpenseAgent)
            # Verify it's also an instance of BaseAgent (through inheritance)
            from agents.base_agent import BaseAgent

            assert isinstance(agent, BaseAgent)

    def test_initializes_with_correct_name(self):
        """Test that ExpenseAgent initializes with correct name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            assert agent.agent_name == "ExpenseAgent"

    def test_initializes_with_correct_description(self):
        """Test that ExpenseAgent initializes with correct description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            expected_description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            assert agent.description == expected_description

    def test_initializes_with_correct_system_prompt(self):
        """Test that ExpenseAgent initializes with correct system prompt."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify the system prompt was passed correctly
            mock_strands_agent.assert_called_once()
            call_args = mock_strands_agent.call_args
            assert call_args[1]["system_prompt"] == EXPENSE_AGENT_SYSTEM_PROMPT


class TestExpenseAgentToolsRegistration:
    """Test that ExpenseAgent registers the correct tools."""

    def test_registers_exactly_three_tools(self):
        """Test that ExpenseAgent registers exactly 3 tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify the tools were passed correctly
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert len(tools) == 3

    def test_registers_preview_claim_tool(self):
        """Test that ExpenseAgent registers preview_claim tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify preview_claim is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert preview_claim in tools

    def test_registers_submit_claim_tool(self):
        """Test that ExpenseAgent registers submit_claim tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify submit_claim is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert submit_claim in tools

    def test_registers_get_claim_tool(self):
        """Test that ExpenseAgent registers get_claim tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify get_claim is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert get_claim in tools

    def test_does_not_register_unexpected_tools(self):
        """Test that ExpenseAgent doesn't register any unexpected tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()

            # Verify only the expected tools are registered
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            expected_tools = {preview_claim, submit_claim, get_claim}

            for tool in tools:
                assert tool in expected_tools


class TestExpenseAgentMetadata:
    """Test ExpenseAgent metadata exposure."""

    def test_exposes_read_only_agent_name(self):
        """Test that ExpenseAgent exposes read-only agent_name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            assert agent.agent_name == "ExpenseAgent"

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_exposes_read_only_description(self):
        """Test that ExpenseAgent exposes read-only description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            expected_description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            assert agent.description == expected_description

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestExpenseAgentStringRepresentation:
    """Test ExpenseAgent string representation."""

    def test_repr_method(self):
        """Test that ExpenseAgent __repr__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            expected_repr = "BaseAgent(name='ExpenseAgent', description='Agent for handling expense claim preview, submission, and retrieval operations.')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that ExpenseAgent __str__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim preview, submission, and retrieval operations."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ExpenseAgent()
            expected_str = "BaseAgent 'ExpenseAgent': Agent for handling expense claim preview, submission, and retrieval operations."
            assert str(agent) == expected_str


class TestExpenseAgentWithCustomModel:
    """Test ExpenseAgent with custom model specification."""

    def test_initializes_with_custom_model(self):
        """Test that ExpenseAgent can be initialized with custom model."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ExpenseAgent"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            agent = ExpenseAgent(model=custom_model)

            # Verify the custom model was passed to StrandsAgent
            call_args = mock_strands_agent.call_args
            assert call_args[1]["model"] == custom_model
