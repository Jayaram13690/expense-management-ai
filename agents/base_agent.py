"""
Base Agent for Strands Agents SDK.

This module provides a base agent class that wraps the Strands Agent SDK.
The BaseAgent is responsible for initializing a Strands Agent and providing
synchronous interfaces for invocation and streaming.

Design Principles:
------------------
- Thin wrapper around Strands Agent SDK
- No business logic
- No domain-specific knowledge
- Pure delegation to Strands Agent
- Synchronous interfaces that wrap async methods
- Read-only metadata exposure
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from strands import Agent as StrandsAgent

from utils.logger import get_logger


class BaseAgent:
    """
    Base agent class that wraps a Strands Agent.

    This class provides a thin wrapper around the Strands Agent SDK, offering
    synchronous interfaces for agent invocation and streaming while maintaining
    all the functionality of the underlying Strands Agent.

    Attributes:
        _agent: The underlying Strands Agent instance
        _logger: Logger instance for this agent
        agent_name: Read-only property for agent name
        description: Read-only property for agent description
    """

    def __init__(
        self,
        model: str | Any | None = None,
        system_prompt: str | None = None,
        tools: list[Any] | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """
        Initialize the BaseAgent with a Strands Agent.

        Args:
            model: Provider for running inference or a string representing the model-id
                for Bedrock to use. Defaults to strands.models.BedrockModel if None.
            system_prompt: System prompt to guide model behavior.
            tools: List of tools to make available to the agent.
            name: Name of the agent.
            description: Description of what the agent does.

        Raises:
            ValueError: If agent name contains path separators.
        """
        self._logger = get_logger(self.__class__.__name__)
        self._logger.debug(
            "Initializing agent '%s'.",
            name,
        )

        self._agent = StrandsAgent(
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            name=name,
            description=description,
        )

        self._logger.info("BaseAgent initialized successfully")
        self._logger.debug(
            "Agent '%s' initialized.",
            name,
        )

    @property
    def agent_name(self) -> str:
        """
        Get the agent name.

        Returns:
            The name of the agent.

        Note:
            This is a read-only property.
        """
        return self._agent.name

    @property
    def description(self) -> str:
        """
        Get the agent description.

        Returns:
            The description of what the agent does, or None if not set.

        Note:
            This is a read-only property.
        """
        return self._agent.description

    def invoke(self, prompt: str, **kwargs: Any) -> Any:
        """
        Invoke the agent synchronously.

        This method provides a synchronous wrapper around the Strands Agent's
        async invoke_async method.

        Args:
            prompt: User input prompt for the agent.
            **kwargs: Additional arguments to pass to the agent invocation.

        Returns:
            The result from the agent invocation.

        Raises:
            RuntimeError: If the async event loop is not available.
            Exception: Any exceptions from the agent invocation.
        """
        self._logger.debug("Invoking agent with prompt: %s", prompt)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(self._agent.invoke_async(prompt, **kwargs))

        self._logger.debug("Agent invocation completed successfully")
        return result

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[Any]:
        """
        Stream responses from the agent.

        This method provides access to the Strands Agent's async stream_async method.

        Args:
            prompt: User input prompt for the agent.
            **kwargs: Additional arguments to pass to the agent streaming.

        Returns:
            An async iterator that yields events from the agent.

        Yields:
            Events from the agent streaming process.

        Raises:
            Exception: Any exceptions from the agent streaming.
        """
        self._logger.debug("Starting agent streaming with prompt: %s", prompt)

        return self._agent.stream_async(prompt, **kwargs)

    def __repr__(self) -> str:
        """
        Get a string representation of the agent.

        Returns:
            String representation including agent name and description.
        """
        return f"BaseAgent(name='{self.agent_name}', description='{self.description}')"

    def __str__(self) -> str:
        """
        Get a human-readable string representation of the agent.

        Returns:
            Human-readable string with agent details.
        """
        return f"BaseAgent '{self.agent_name}': {self.description or 'No description'}"
