"""
Test suite for EmployeeAgent.

This module validates the EmployeeAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

from unittest.mock import MagicMock, patch

import pytest

from agents.employee_agent import EmployeeAgent
from prompts.employee_prompt import EMPLOYEE_AGENT_SYSTEM_PROMPT
from tools.employee_tools import get_employee_details, list_employee_claims


class TestEmployeeAgentInitialization:
    """Test EmployeeAgent initialization and inheritance."""

    def test_inherits_from_base_agent(self):
        """Test that EmployeeAgent inherits from BaseAgent."""
        with patch("agents.base_agent.StrandsAgent"):
            agent = EmployeeAgent()
            assert isinstance(agent, EmployeeAgent)
            # Verify it's also an instance of BaseAgent (through inheritance)
            from agents.base_agent import BaseAgent

            assert isinstance(agent, BaseAgent)

    def test_initializes_with_correct_name(self):
        """Test that EmployeeAgent initializes with correct name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_agent_instance.description = (
                "Agent for retrieving employee information and claim history."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            assert agent.agent_name == "EmployeeAgent"

    def test_initializes_with_correct_description(self):
        """Test that EmployeeAgent initializes with correct description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_agent_instance.description = (
                "Agent for retrieving employee information and claim history."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            expected_description = "Agent for retrieving employee information and claim history."
            assert agent.description == expected_description

    def test_initializes_with_correct_system_prompt(self):
        """Test that EmployeeAgent initializes with correct system prompt."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()

            # Verify the system prompt was passed correctly
            mock_strands_agent.assert_called_once()
            call_args = mock_strands_agent.call_args
            assert call_args[1]["system_prompt"] == EMPLOYEE_AGENT_SYSTEM_PROMPT


class TestEmployeeAgentToolsRegistration:
    """Test that EmployeeAgent registers the correct tools."""

    def test_registers_exactly_two_tools(self):
        """Test that EmployeeAgent registers exactly 2 tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()

            # Verify the tools were passed correctly
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert len(tools) == 2

    def test_registers_get_employee_details_tool(self):
        """Test that EmployeeAgent registers get_employee_details tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()

            # Verify get_employee_details is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert get_employee_details in tools

    def test_registers_list_employee_claims_tool(self):
        """Test that EmployeeAgent registers list_employee_claims tool."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()

            # Verify list_employee_claims is in the registered tools
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            assert list_employee_claims in tools

    def test_does_not_register_unexpected_tools(self):
        """Test that EmployeeAgent doesn't register any unexpected tools."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()

            # Verify only the expected tools are registered
            call_args = mock_strands_agent.call_args
            tools = call_args[1]["tools"]
            expected_tools = {get_employee_details, list_employee_claims}

            for tool in tools:
                assert tool in expected_tools


class TestEmployeeAgentMetadata:
    """Test EmployeeAgent metadata exposure."""

    def test_exposes_read_only_agent_name(self):
        """Test that EmployeeAgent exposes read-only agent_name."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            assert agent.agent_name == "EmployeeAgent"

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_exposes_read_only_description(self):
        """Test that EmployeeAgent exposes read-only description."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_agent_instance.description = (
                "Agent for retrieving employee information and claim history."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            expected_description = "Agent for retrieving employee information and claim history."
            assert agent.description == expected_description

            # Verify it's read-only
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestEmployeeAgentStringRepresentation:
    """Test EmployeeAgent string representation."""

    def test_repr_method(self):
        """Test that EmployeeAgent __repr__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_agent_instance.description = (
                "Agent for retrieving employee information and claim history."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            expected_repr = "BaseAgent(name='EmployeeAgent', description='Agent for retrieving employee information and claim history.')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that EmployeeAgent __str__ works correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_agent_instance.description = (
                "Agent for retrieving employee information and claim history."
            )
            mock_strands_agent.return_value = mock_agent_instance

            agent = EmployeeAgent()
            expected_str = "BaseAgent 'EmployeeAgent': Agent for retrieving employee information and claim history."
            assert str(agent) == expected_str


class TestEmployeeAgentWithCustomModel:
    """Test EmployeeAgent with custom model specification."""

    def test_initializes_with_custom_model(self):
        """Test that EmployeeAgent can be initialized with custom model."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "EmployeeAgent"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "anthropic.claude-3-sonnet-20240229-v1:0"
            agent = EmployeeAgent(model=custom_model)

            # Verify the custom model was passed to StrandsAgent
            call_args = mock_strands_agent.call_args
            assert call_args[1]["model"] == custom_model
