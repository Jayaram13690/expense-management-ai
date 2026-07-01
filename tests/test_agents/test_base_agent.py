"""
Test suite for BaseAgent.

This module validates the BaseAgent implementation without modifying production code.
All external dependencies are mocked to ensure isolated testing.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from agents.base_agent import BaseAgent


class TestBaseAgentInitialization:
    """Test BaseAgent initialization and basic properties."""

    def test_initialization_with_defaults(self):
        """Test that BaseAgent initializes with default parameters."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "Strands Agents"
            mock_agent_instance.description = None
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent()

            # Verify StrandsAgent was initialized with defaults
            mock_strands_agent.assert_called_once_with(
                model=None, system_prompt=None, tools=None, name=None, description=None
            )

            # Verify agent properties
            assert agent.agent_name == "Strands Agents"
            assert agent.description is None

    def test_initialization_with_custom_parameters(self):
        """Test that BaseAgent initializes with custom parameters."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "CustomAgent"
            mock_agent_instance.description = "Custom description"
            mock_strands_agent.return_value = mock_agent_instance

            custom_model = "test-model"
            custom_prompt = "test prompt"
            custom_tools = [MagicMock(), MagicMock()]

            agent = BaseAgent(
                model=custom_model,
                system_prompt=custom_prompt,
                tools=custom_tools,
                name="CustomAgent",
                description="Custom description",
            )

            # Verify StrandsAgent was initialized with custom parameters
            mock_strands_agent.assert_called_once_with(
                model=custom_model,
                system_prompt=custom_prompt,
                tools=custom_tools,
                name="CustomAgent",
                description="Custom description",
            )

            # Verify agent properties
            assert agent.agent_name == "CustomAgent"
            assert agent.description == "Custom description"

    def test_agent_name_property_is_read_only(self):
        """Test that agent_name is a read-only property."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            # Verify property access works
            assert agent.agent_name == "TestAgent"

            # Verify it's read-only by checking it's a property
            with pytest.raises(AttributeError):
                agent.agent_name = "NewName"

    def test_description_property_is_read_only(self):
        """Test that description is a read-only property."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = "Test description"
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(description="Test description")

            # Verify property access works
            assert agent.description == "Test description"

            # Verify it's read-only by checking it's a property
            with pytest.raises(AttributeError):
                agent.description = "NewDescription"


class TestBaseAgentStringRepresentation:
    """Test BaseAgent string representation methods."""

    def test_repr_method(self):
        """Test that __repr__ returns correct string representation."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = "Test description"
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent", description="Test description")

            expected_repr = "BaseAgent(name='TestAgent', description='Test description')"
            assert repr(agent) == expected_repr

    def test_repr_with_none_description(self):
        """Test that __repr__ handles None description correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = None
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            expected_repr = "BaseAgent(name='TestAgent', description='None')"
            assert repr(agent) == expected_repr

    def test_str_method(self):
        """Test that __str__ returns correct human-readable representation."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = "Test description"
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent", description="Test description")

            expected_str = "BaseAgent 'TestAgent': Test description"
            assert str(agent) == expected_str

    def test_str_with_none_description(self):
        """Test that __str__ handles None description correctly."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = None
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            expected_str = "BaseAgent 'TestAgent': No description"
            assert str(agent) == expected_str


class TestBaseAgentInvokeMethod:
    """Test BaseAgent invoke() method functionality."""

    def test_invoke_delegates_to_strands_agent(self):
        """Test that invoke() delegates to the underlying Strands Agent."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            # Create mock agent with async invoke_async method
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"
            mock_agent_instance.description = "Test description"

            # Create an async mock for invoke_async
            async def mock_invoke_async(prompt, **kwargs):
                return "mock_result"

            mock_agent_instance.invoke_async = mock_invoke_async
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            # Test synchronous invoke
            result = agent.invoke("test prompt", key="value")

            # Verify the result
            assert result == "mock_result"

    def test_invoke_with_existing_event_loop(self):
        """Test that invoke() works with an existing event loop."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            # Create mock agent
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"

            async def mock_invoke_async(prompt, **kwargs):
                return "result_with_loop"

            mock_agent_instance.invoke_async = mock_invoke_async
            mock_strands_agent.return_value = mock_agent_instance

            # Create an event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                agent = BaseAgent(name="TestAgent")
                result = agent.invoke("test")
                assert result == "result_with_loop"
            finally:
                loop.close()

    def test_invoke_creates_new_event_loop_if_needed(self):
        """Test that invoke() creates a new event loop if none exists."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            with patch("agents.base_agent.asyncio.get_event_loop") as mock_get_loop:
                # Simulate no existing event loop
                mock_get_loop.side_effect = RuntimeError("No event loop")

                mock_agent_instance = MagicMock()
                mock_agent_instance.name = "TestAgent"

                async def mock_invoke_async(prompt, **kwargs):
                    return "result_new_loop"

                mock_agent_instance.invoke_async = mock_invoke_async
                mock_strands_agent.return_value = mock_agent_instance

                agent = BaseAgent(name="TestAgent")
                result = agent.invoke("test")
                assert result == "result_new_loop"

    def test_invoke_propagates_exceptions(self):
        """Test that invoke() propagates exceptions from the underlying agent."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"

            async def mock_invoke_async(prompt, **kwargs):
                raise ValueError("Test error")

            mock_agent_instance.invoke_async = mock_invoke_async
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            with pytest.raises(ValueError, match="Test error"):
                agent.invoke("test")


class TestBaseAgentStreamMethod:
    """Test BaseAgent stream() method functionality."""

    def test_stream_delegates_to_strands_agent(self):
        """Test that stream() delegates to the underlying Strands Agent's stream_async."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"

            # Create an async generator for stream_async
            async def mock_stream_async(prompt, **kwargs):
                yield {"data": "chunk1"}
                yield {"data": "chunk2"}

            mock_agent_instance.stream_async = mock_stream_async
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            # Test that stream returns the async iterator
            stream_result = agent.stream("test prompt")

            # Verify it's the correct method being called
            assert hasattr(stream_result, "__aiter__")

    def test_stream_delegates_correctly(self):
        """Test that stream() delegates to the underlying Strands Agent's stream_async."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            mock_agent_instance = MagicMock()
            mock_agent_instance.name = "TestAgent"

            # Create a proper async generator mock
            async def mock_stream_async(prompt, **kwargs):
                yield {"data": "test_chunk"}

            # Mock the stream_async method to return the generator
            mock_agent_instance.stream_async = mock_stream_async
            mock_strands_agent.return_value = mock_agent_instance

            agent = BaseAgent(name="TestAgent")

            # Test that stream returns the async iterator
            stream_result = agent.stream("test prompt")

            # Verify it's an async generator by checking for __aiter__ attribute
            # Note: async generators have __aiter__ but are not callable
            import types

            assert isinstance(stream_result, types.AsyncGeneratorType)


class TestBaseAgentErrorHandling:
    """Test BaseAgent error handling and edge cases."""

    def test_initialization_with_invalid_agent_name(self):
        """Test that initialization raises ValueError for invalid agent names."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            # Simulate StrandsAgent raising ValueError for invalid name
            mock_strands_agent.side_effect = ValueError("Invalid agent name")

            with pytest.raises(ValueError, match="Invalid agent name"):
                BaseAgent(name="invalid/name")

    def test_invoke_with_runtime_error(self):
        """Test that invoke() handles RuntimeError during event loop creation."""
        with patch("agents.base_agent.StrandsAgent") as mock_strands_agent:
            with patch("agents.base_agent.asyncio.get_event_loop") as mock_get_loop:
                with patch("agents.base_agent.asyncio.new_event_loop") as mock_new_loop:
                    # Simulate failure to create new event loop
                    mock_get_loop.side_effect = RuntimeError("No event loop")
                    mock_new_loop.side_effect = RuntimeError("Cannot create loop")

                    mock_agent_instance = MagicMock()
                    mock_agent_instance.name = "TestAgent"
                    mock_strands_agent.return_value = mock_agent_instance

                    agent = BaseAgent(name="TestAgent")

                    with pytest.raises(RuntimeError, match="Cannot create loop"):
                        agent.invoke("test")
