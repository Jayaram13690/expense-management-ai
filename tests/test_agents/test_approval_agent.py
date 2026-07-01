"""
Test suite for ApprovalAgent.

This module validates the ApprovalAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.approval_agent import ApprovalAgent
from prompts.approval_prompt import APPROVAL_AGENT_SYSTEM_PROMPT
from tools.approval_tools import (
    approve_claim,
    list_manager_queue,
    list_pending_claims,
    reject_claim,
)


class TestApprovalAgentInitialization:
    """Test ApprovalAgent initialization and inheritance."""

    def test_inherits_from_base_agent(self):
        """Test that ApprovalAgent inherits from BaseAgent."""
        with patch("agents.base_agent.StrandsAgent"):
            agent = ApprovalAgent()
            assert isinstance(agent, ApprovalAgent)
            # Verify it's also an instance of BaseAgent (through inheritance)
            from agents.base_agent import BaseAgent

            assert isinstance(agent, BaseAgent)

    def test_initializes_with_correct_name(self):
        """Test that ApprovalAgent initializes with correct name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            assert agent.agent_name == "ApprovalAgent"

    def test_initializes_with_correct_description(self):
        """Test that ApprovalAgent initializes with correct description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            expected_description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            assert agent.description == expected_description

    def test_initializes_with_correct_system_prompt(self):
        """Test that ApprovalAgent initializes with correct system prompt."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify the system prompt was passed correctly
            mock_strands_agent.assert_called_once()
            call_args = mock_strands_agent.call_args
            assert call_args[1]["system_prompt"] == APPROVAL_AGENT_SYSTEM_PROMPT


class TestApprovalAgentToolsRegistration:
    """Test that ApprovalAgent registers the correct tools."""

    def test_registers_exactly_four_tools(self):
        """Test that ApprovalAgent registers exactly 4 tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify the tools were passed correctly
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert len(tools) == 4

    def test_registers_approve_claim_tool(self):
        """Test that ApprovalAgent registers approve_claim tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify approve_claim is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert approve_claim in tools

    def test_registers_reject_claim_tool(self):
        """Test that ApprovalAgent registers reject_claim tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify reject_claim is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert reject_claim in tools

    def test_registers_list_pending_claims_tool(self):
        """Test that ApprovalAgent registers list_pending_claims tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify list_pending_claims is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert list_pending_claims in tools

    def test_registers_list_manager_queue_tool(self):
        """Test that ApprovalAgent registers list_manager_queue tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify list_manager_queue is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert list_manager_queue in tools

    def test_does_not_register_unexpected_tools(self):
        """Test that ApprovalAgent doesn't register any unexpected tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()

            # Verify only the expected tools are registered
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            expected_tools = {approve_claim, reject_claim, list_pending_claims, list_manager_queue}

            for tool in tools:
                assert tool in expected_tools


class TestApprovalAgentMetadata:
    """Test ApprovalAgent metadata exposure."""

    def test_exposes_read_only_agent_name(self):
        """Test that ApprovalAgent exposes read-only agent_name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            assert agent.agent_name == "ApprovalAgent"

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_exposes_read_only_description(self):
        """Test that ApprovalAgent exposes read-only description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            expected_description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            assert agent.description == expected_description

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestApprovalAgentStringRepresentation:
    """Test ApprovalAgent string representation."""

    def test_repr_method(self):
        """Test that ApprovalAgent __repr__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            expected_repr = "BaseAgent(name='ApprovalAgent', description='Agent for handling expense claim approval workflows and queue management.')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that ApprovalAgent __str__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_agent_instance.description = (
                "Agent for handling expense claim approval workflows and queue management."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ApprovalAgent()
            expected_str = "BaseAgent 'ApprovalAgent': Agent for handling expense claim approval workflows and queue management."
            assert str(agent) == expected_str


class TestApprovalAgentWithCustomModel:
    """Test ApprovalAgent with custom model specification."""

    def test_initializes_with_custom_model(self):
        """Test that ApprovalAgent can be initialized with custom model."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ApprovalAgent"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            agent = ApprovalAgent(model=custom_model)

            # Verify the custom model was passed to StrandsAgent
            call_args = mock_strands_agent.call_args
            assert call_args[1]["model"] == custom_model
