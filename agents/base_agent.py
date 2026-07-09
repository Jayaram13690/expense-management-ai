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

from pydantic import BaseModel
from strands import Agent as StrandsAgent
from strands import ModelRetryStrategy
from strands.models import BedrockModel

from config.settings import settings
from utils.logger import get_logger


class BaseAgent:
    """
    Base agent class that wraps a Strands Agent.

    This class provides a thin wrapper around the Strands Agent SDK, offering
    synchronous interfaces for agent invocation and streaming while maintaining
    all the functionality of the underlying Strands Agent.
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
        Initialize the BaseAgent.

        Args:
            model:
                Optional model provider.

                If None, the default Bedrock model configured in
                config.settings will be used.
            system_prompt:
                Agent system prompt.
            tools:
                Tools available to the agent.
            name:
                Agent name.
            description:
                Agent description.
        """

        self._logger = get_logger(self.__class__.__name__)

        self._logger.debug("Initializing agent '%s'.", name)

        #
        # Resolve model
        #
        resolved_model = model

        if resolved_model is None:
            self._logger.info(
                "Using configured Bedrock model '%s' in region '%s'.",
                settings.aws.bedrock_model_id,
                settings.aws.aws_region,
            )

            resolved_model = BedrockModel(
                model_id=settings.aws.bedrock_model_id,
                region_name=settings.aws.aws_region,
                temperature=0.1,
                top_p=0.9,
                max_tokens=450,
                guardrail_id=settings.aws.bedrock_guardrail_id,
                guardrail_version=settings.aws.bedrock_guardrail_version,
                # Recommended options
                guardrail_trace="enabled",
                guardrail_redact_input=True,
                guardrail_redact_output=True,
                guardrail_latest_message=True,
            )

        else:
            self._logger.info("Using injected model for agent '%s'.", name)

        # Evaluate tools if provided
        wrapped_tools = tools
        if tools:
            from evaluation.tool_evaluator import ToolEvaluator

            evaluator = ToolEvaluator()
            wrapped_tools = [evaluator.evaluate_tool_call(t) for t in tools]

        #
        # Create Strands Agent
        #
        self._agent = StrandsAgent(
            model=resolved_model,
            system_prompt=system_prompt,
            tools=wrapped_tools,
            name=name,
            description=description,
            retry_strategy=ModelRetryStrategy(
                max_attempts=3,  # Total attempts (including first try)
                initial_delay=2,  # Seconds before first retry
                max_delay=60,
            ),
        )

        self._logger.info("BaseAgent initialized successfully.")

    @property
    def agent_name(self) -> str:
        """Return the configured agent name."""
        return self._agent.name

    @property
    def description(self) -> str:
        """Return the configured agent description."""
        return self._agent.description

    def invoke(
        self,
        prompt: str,
        *,
        structured_output_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Invoke the Strands agent synchronously.
        """

        self._logger.debug("Invoking agent '%s'.", self.agent_name)
        self._logger.debug("Prompt:\n%s", prompt)

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.invoke_async(
                    prompt,
                    structured_output_model=structured_output_model,
                    **kwargs,
                )
            )
        finally:
            loop.close()
            asyncio.set_event_loop(None)

        # try:
        #     loop = asyncio.get_event_loop()
        # except RuntimeError:
        #     loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(loop)

        # result = loop.run_until_complete(
        #     self.invoke_async(
        #         prompt,
        #         structured_output_model=structured_output_model,
        #         **kwargs,
        #     )
        # )

        self._logger.debug("Agent invocation completed.")

        return result

    async def invoke_async(
        self,
        prompt: str,
        *,
        structured_output_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Invoke the Strands agent asynchronously.
        """

        return await self._agent.invoke_async(
            prompt,
            structured_output_model=structured_output_model,
            **kwargs,
        )

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[Any]:
        """
        Stream agent responses.
        """

        return self._agent.stream_async(
            prompt,
            **kwargs,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='{self.agent_name}', description='{self.description}')"
        )

    def __str__(self) -> str:
        return f"{self.agent_name} ({self.description or 'No description'})"
