"""
Test suite for PolicyAgent.

This module validates the PolicyAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.policy_agent import PolicyAgent
from prompts.policy_prompt import POLICY_AGENT_SYSTEM_PROMPT
from tools.policy_tools import get_expense_category, get_policy


class TestPolicyAgentInitialization:
    """Test PolicyAgent initialization and inheritance."""

    def test_inherits_from_base_agent(self):
        """Test that PolicyAgent inherits from BaseAgent."""
        with patch("agents.base_agent.StrandsAgent"):
            agent = PolicyAgent()
            assert isinstance(agent, PolicyAgent)
            # Verify it's also an instance of BaseAgent (through inheritance)
            from agents.base_agent import BaseAgent

            assert isinstance(agent, BaseAgent)

    def test_initializes_with_correct_name(self):
        """Test that PolicyAgent initializes with correct name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_agent_instance.description = (
                "Agent for retrieving policy information and expense category details."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            assert agent.agent_name == "PolicyAgent"

    def test_initializes_with_correct_description(self):
        """Test that PolicyAgent initializes with correct description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_agent_instance.description = (
                "Agent for retrieving policy information and expense category details."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            expected_description = (
                "Agent for retrieving policy information and expense category details."
            )
            assert agent.description == expected_description

    def test_initializes_with_correct_system_prompt(self):
        """Test that PolicyAgent initializes with correct system prompt."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()

            # Verify the system prompt was passed correctly
            mock_strands_agent.assert_called_once()
            call_args = mock_strands_agent.call_args
            assert call_args[1]["system_prompt"] == POLICY_AGENT_SYSTEM_PROMPT


class TestPolicyAgentToolsRegistration:
    """Test that PolicyAgent registers the correct tools."""

    def test_registers_exactly_two_tools(self):
        """Test that PolicyAgent registers exactly 2 tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()

            # Verify the tools were passed correctly
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert len(tools) == 2

    def test_registers_get_policy_tool(self):
        """Test that PolicyAgent registers get_policy tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()

            # Verify get_policy is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert get_policy in tools

    def test_registers_get_expense_category_tool(self):
        """Test that PolicyAgent registers get_expense_category tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()

            # Verify get_expense_category is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert get_expense_category in tools

    def test_does_not_register_unexpected_tools(self):
        """Test that PolicyAgent doesn't register any unexpected tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()

            # Verify only the expected tools are registered
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            expected_tools = {get_policy, get_expense_category}

            for tool in tools:
                assert tool in expected_tools


class TestPolicyAgentMetadata:
    """Test PolicyAgent metadata exposure."""

    def test_exposes_read_only_agent_name(self):
        """Test that PolicyAgent exposes read-only agent_name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            assert agent.agent_name == "PolicyAgent"

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_exposes_read_only_description(self):
        """Test that PolicyAgent exposes read-only description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_agent_instance.description = (
                "Agent for retrieving policy information and expense category details."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            expected_description = (
                "Agent for retrieving policy information and expense category details."
            )
            assert agent.description == expected_description

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestPolicyAgentStringRepresentation:
    """Test PolicyAgent string representation."""

    def test_repr_method(self):
        """Test that PolicyAgent __repr__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_agent_instance.description = (
                "Agent for retrieving policy information and expense category details."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            expected_repr = "BaseAgent(name='PolicyAgent', description='Agent for retrieving policy information and expense category details.')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that PolicyAgent __str__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_agent_instance.description = (
                "Agent for retrieving policy information and expense category details."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = PolicyAgent()
            expected_str = "BaseAgent 'PolicyAgent': Agent for retrieving policy information and expense category details."
            assert str(agent) == expected_str


class TestPolicyAgentWithCustomModel:
    """Test PolicyAgent with custom model specification."""

    def test_initializes_with_custom_model(self):
        """Test that PolicyAgent can be initialized with custom model."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "PolicyAgent"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            agent = PolicyAgent(model=custom_model)

            # Verify the custom model was passed to StrandsAgent
            call_args = mock_strands_agent.call_args
            assert call_args[1]["model"] == custom_model
