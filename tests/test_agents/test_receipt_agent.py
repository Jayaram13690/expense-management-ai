"""
Test suite for ReceiptAgent.

This module validates the ReceiptAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.receipt_agent import ReceiptAgent
from prompts.receipt_prompt import RECEIPT_AGENT_SYSTEM_PROMPT
from tools.receipt_tools import get_receipt_status, upload_receipt


class TestReceiptAgentInitialization:
    """Test ReceiptAgent initialization and inheritance."""

    def test_inherits_from_base_agent(self):
        """Test that ReceiptAgent inherits from BaseAgent."""
        with patch("agents.base_agent.StrandsAgent"):
            agent = ReceiptAgent()
            assert isinstance(agent, ReceiptAgent)
            # Verify it's also an instance of BaseAgent (through inheritance)
            from agents.base_agent import BaseAgent

            assert isinstance(agent, BaseAgent)

    def test_initializes_with_correct_name(self):
        """Test that ReceiptAgent initializes with correct name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_agent_instance.description = (
                "Agent for handling receipt document upload and status tracking."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            assert agent.agent_name == "ReceiptAgent"

    def test_initializes_with_correct_description(self):
        """Test that ReceiptAgent initializes with correct description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_agent_instance.description = (
                "Agent for handling receipt document upload and status tracking."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            expected_description = "Agent for handling receipt document upload and status tracking."
            assert agent.description == expected_description

    def test_initializes_with_correct_system_prompt(self):
        """Test that ReceiptAgent initializes with correct system prompt."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()

            # Verify the system prompt was passed correctly
            mock_strands_agent.assert_called_once()
            call_args = mock_strands_agent.call_args
            assert call_args[1]["system_prompt"] == RECEIPT_AGENT_SYSTEM_PROMPT


class TestReceiptAgentToolsRegistration:
    """Test that ReceiptAgent registers the correct tools."""

    def test_registers_exactly_two_tools(self):
        """Test that ReceiptAgent registers exactly 2 tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()

            # Verify the tools were passed correctly
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert len(tools) == 2

    def test_registers_upload_receipt_tool(self):
        """Test that ReceiptAgent registers upload_receipt tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()

            # Verify upload_receipt is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert upload_receipt in tools

    def test_registers_get_receipt_status_tool(self):
        """Test that ReceiptAgent registers get_receipt_status tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()

            # Verify get_receipt_status is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert get_receipt_status in tools

    def test_does_not_register_unexpected_tools(self):
        """Test that ReceiptAgent doesn't register any unexpected tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()

            # Verify only the expected tools are registered
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            expected_tools = {upload_receipt, get_receipt_status}

            for tool in tools:
                assert tool in expected_tools


class TestReceiptAgentMetadata:
    """Test ReceiptAgent metadata exposure."""

    def test_exposes_read_only_agent_name(self):
        """Test that ReceiptAgent exposes read-only agent_name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            assert agent.agent_name == "ReceiptAgent"

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_exposes_read_only_description(self):
        """Test that ReceiptAgent exposes read-only description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_agent_instance.description = (
                "Agent for handling receipt document upload and status tracking."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            expected_description = "Agent for handling receipt document upload and status tracking."
            assert agent.description == expected_description

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestReceiptAgentStringRepresentation:
    """Test ReceiptAgent string representation."""

    def test_repr_method(self):
        """Test that ReceiptAgent __repr__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_agent_instance.description = (
                "Agent for handling receipt document upload and status tracking."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            expected_repr = "BaseAgent(name='ReceiptAgent', description='Agent for handling receipt document upload and status tracking.')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that ReceiptAgent __str__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_agent_instance.description = (
                "Agent for handling receipt document upload and status tracking."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = ReceiptAgent()
            expected_str = "BaseAgent 'ReceiptAgent': Agent for handling receipt document upload and status tracking."
            assert str(agent) == expected_str


class TestReceiptAgentWithCustomModel:
    """Test ReceiptAgent with custom model specification."""

    def test_initializes_with_custom_model(self):
        """Test that ReceiptAgent can be initialized with custom model."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "ReceiptAgent"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            agent = ReceiptAgent(model=custom_model)

            # Verify the custom model was passed to StrandsAgent
            call_args = mock_strands_agent.call_args
            assert call_args[1]["model"] == custom_model
