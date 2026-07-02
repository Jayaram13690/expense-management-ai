"""
Coordinator Conversation Integration.

This module provides conversation management capabilities for the Coordinator.
It enables the Coordinator to conduct conversations by determining what information
is needed, what has been collected, and what should be asked next.

Design Principles:
------------------
- Pure conversation orchestration - no workflow execution
- Uses only existing Conversation Layer (intents, requirements, prompts)
- No business logic, routing, or agent invocation
- No direct access to services, repositories, or tools
- Clean separation from execution concerns
- Fully unit testable without external dependencies
"""

from __future__ import annotations

from typing import Any

from conversation.field_mappings import get_prompt_for_field
from conversation.intent_mappings import get_requirements_for_intent
from conversation.intents import ConversationIntent
from conversation.requirements import IntentRequirements

# Import for type hints (avoid circular import)
from coordinator.builders import CoordinatorRequestBuilder


class ConversationManager:
    """
    Manages conversation state and determines what to ask next.

    This class is responsible for tracking conversation progress, determining
    missing information, and selecting appropriate prompts.
    """

    def __init__(self, request_builder: CoordinatorRequestBuilder | None = None) -> None:
        """Initialize the conversation manager."""
        self._current_intent: ConversationIntent | None = None
        self._current_requirements: IntentRequirements | None = None
        self._request_builder: CoordinatorRequestBuilder | None = request_builder

    def start_conversation(self, intent: ConversationIntent) -> None:
        """Start a new conversation for the specified intent."""
        self._current_intent = intent
        self._current_requirements = self._get_requirements_for_intent(intent)

    def _get_requirements_for_intent(self, intent: ConversationIntent) -> IntentRequirements | None:
        """Get the IntentRequirements for the specified intent."""
        requirements = get_requirements_for_intent(intent)
        if requirements is None:
            # Return None for unknown intents to allow graceful handling
            return None
        return requirements

    def collect_field(self, field_name: str, value: Any) -> None:
        """Mark a field as collected with the given value."""
        if self._request_builder is not None:
            self._request_builder.add_field(field_name, value)

    def get_missing_required_fields(self) -> list[str]:
        """Get list of required fields that haven't been collected yet."""
        if self._current_requirements is None or self._request_builder is None:
            return []

        required_fields = list(self._current_requirements.required_fields)
        collected_fields = set(self._request_builder.get_collected_data().keys())
        return [field for field in required_fields if field not in collected_fields]

    def get_next_prompt(self) -> str | None:
        """Get the next conversational prompt to ask the user."""
        missing_fields = self.get_missing_required_fields()

        if not missing_fields:
            return None  # No more fields needed

        # Get prompt for the first missing field
        first_missing_field = missing_fields[0]
        return get_prompt_for_field(first_missing_field)

    def is_ready_to_execute(self) -> bool:
        """Check if all required fields have been collected."""
        return len(self.get_missing_required_fields()) == 0

    def current_requirements(self) -> IntentRequirements | None:
        """Get the current IntentRequirements for this conversation."""
        return self._current_requirements

    def current_intent(self) -> ConversationIntent | None:
        """Get the current ConversationIntent for this conversation."""
        return self._current_intent

    def reset(self) -> None:
        """Reset the conversation manager to initial state."""
        self._current_intent = None
        self._current_requirements = None


__all__ = ["ConversationManager"]
