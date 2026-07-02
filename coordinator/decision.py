"""
Decision Engine Models.

This module defines the immutable decision models for the Coordinator's Decision Engine.
These models represent the decisions made by the Decision Engine without containing
any execution logic or business processing.

Design Principles:
------------------
- Immutable data structures using frozen dataclasses
- Pure decision representation - no execution logic
- Type-safe enums for decision categories
- Comprehensive metadata for future LLM integration
- No dependencies on services, agents, or tools
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from conversation.intents import ConversationIntent
from conversation.requirements import IntentRequirements
from coordinator.builders import CoordinatorRequestBuilder
from coordinator.state import WorkflowState


class DecisionType(StrEnum):
    """
    Enumeration of decision types that the Decision Engine can return.

    Each decision type represents a specific action that should be taken
    by the Coordinator, without containing any execution logic.
    """

    # Continue gathering information from user
    CONTINUE_CONVERSATION = "continue_conversation"

    # All requirements met, proceed with workflow execution
    EXECUTE_WORKFLOW = "execute_workflow"

    # Wait for user confirmation before proceeding
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"

    # Wait for receipt upload from user
    WAIT_FOR_RECEIPT = "wait_for_receipt"

    # Wait for manager approval
    WAIT_FOR_MANAGER = "wait_for_manager"

    # Workflow completed successfully
    COMPLETE = "complete"

    # Workflow cancelled by user
    CANCEL = "cancel"

    # Error condition encountered
    ERROR = "error"

    # Unknown or unsupported request
    UNKNOWN = "unknown"


class ExecutionMode(StrEnum):
    """
    Enumeration of execution modes for workflow execution.

    These modes represent how workflows should be executed, but contain
    no actual execution logic. This is metadata only for future implementation.
    """

    # Execute operations sequentially
    SEQUENTIAL = "sequential"

    # Execute operations in parallel where possible
    PARALLEL = "parallel"

    # No execution required
    NONE = "none"


@dataclass(frozen=True)
class Decision:
    """
    Immutable decision model representing what the Coordinator should do next.

    This class captures the Decision Engine's determination of the appropriate
    next action without containing any logic to perform that action.

    Attributes:
        decision_type:
            The type of decision being made (what should happen next)

        next_agent:
            Optional identifier of the agent that should handle this decision

        reason:
            Human-readable explanation of why this decision was made

        execution_mode:
            How the workflow should be executed (sequential, parallel, none)

        requires_confirmation:
            Whether this decision requires user confirmation before proceeding

        requires_user_input:
            Whether this decision requires additional user input

        missing_fields:
            List of fields that are still required to proceed

        metadata:
            Additional context and information about the decision
    """

    decision_type: DecisionType
    next_agent: str | None = None
    reason: str = ""
    execution_mode: ExecutionMode = ExecutionMode.NONE
    requires_confirmation: bool = False
    requires_user_input: bool = False
    missing_fields: Sequence[str] = ()
    metadata: dict[str, str] = None

    def __post_init__(self) -> None:
        """Ensure metadata is properly initialized."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class DecisionEngine:
    """
    Decision Engine for the Coordinator.

    The Decision Engine determines what should happen next based on the current
    conversation state, requirements, and collected information. It never
    executes any actions, invokes agents, or performs workflows - it only returns
    decisions.

    This class is designed to be replaceable with an LLM-based decision maker
    in the future without changing the Coordinator's public API.

    Design Principles:
        - Pure decision making - no execution logic
        - Deterministic rules (today) with LLM abstraction (future)
        - No dependencies on agents, services, or tools
        - No side effects - only inspection and decision
        - Comprehensive logging for debugging
    """

    def decide(
        self,
        intent: ConversationIntent | None,
        requirements: IntentRequirements | None,
        request_builder: CoordinatorRequestBuilder,
        current_state: WorkflowState,
    ) -> Decision:
        """
        Determine what should happen next based on current conversation state.

        Args:
            intent: The current conversation intent
            requirements: The intent requirements (if any)
            request_builder: The request builder containing collected data
            current_state: The current workflow state

        Returns:
            Decision: What the Coordinator should do next

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate inputs
        if request_builder is None:
            raise ValueError("request_builder cannot be None")

        # Handle unknown intent
        if intent is None or intent == ConversationIntent.UNKNOWN:
            return self._handle_unknown_intent()

        # Handle missing requirements
        if requirements is None:
            return self._handle_missing_requirements(intent)

        # Get collected fields and missing fields
        collected_data = request_builder.get_collected_data()
        collected_fields = set(collected_data.keys())
        required_fields = set(requirements.required_fields)
        missing_fields = list(required_fields - collected_fields)

        # Apply decision rules

        # Rule 1: If missing fields exist, continue conversation
        if missing_fields:
            return self._continue_conversation_decision(
                intent=intent, missing_fields=missing_fields, requirements=requirements
            )

        # Rule 2: If confirmation is required, wait for confirmation
        if requirements.confirmation_required:
            return self._wait_for_confirmation_decision(intent=intent)

        # Rule 3: Determine execution mode based on intent
        execution_mode = self._determine_execution_mode(intent)

        # Rule 4: Ready to execute workflow
        return self._execute_workflow_decision(intent=intent, execution_mode=execution_mode)

    def _handle_unknown_intent(self) -> Decision:
        """Handle unknown intent by returning UNKNOWN decision."""
        return Decision(
            decision_type=DecisionType.UNKNOWN,
            reason="Unknown or unsupported intent",
            execution_mode=ExecutionMode.NONE,
            requires_user_input=True,
            metadata={"context": "unknown_intent"},
        )

    def _handle_missing_requirements(self, intent: ConversationIntent) -> Decision:
        """Handle missing requirements by returning ERROR decision."""
        return Decision(
            decision_type=DecisionType.ERROR,
            reason=f"No requirements defined for intent: {intent}",
            execution_mode=ExecutionMode.NONE,
            metadata={"intent": intent, "context": "missing_requirements"},
        )

    def _continue_conversation_decision(
        self,
        intent: ConversationIntent,
        missing_fields: list[str],
        requirements: IntentRequirements,
    ) -> Decision:
        """Create decision to continue conversation and gather missing fields."""
        return Decision(
            decision_type=DecisionType.CONTINUE_CONVERSATION,
            reason=f"Missing required fields for {intent}",
            execution_mode=ExecutionMode.NONE,
            requires_user_input=True,
            missing_fields=missing_fields,
            metadata={
                "intent": intent,
                "missing_count": str(len(missing_fields)),
                "total_required": str(len(requirements.required_fields)),
            },
        )

    def _wait_for_confirmation_decision(self, intent: ConversationIntent) -> Decision:
        """Create decision to wait for user confirmation."""
        return Decision(
            decision_type=DecisionType.WAIT_FOR_CONFIRMATION,
            reason=f"Confirmation required for {intent}",
            execution_mode=ExecutionMode.NONE,
            requires_confirmation=True,
            metadata={"intent": intent, "context": "confirmation_required"},
        )

    def _execute_workflow_decision(
        self, intent: ConversationIntent, execution_mode: ExecutionMode
    ) -> Decision:
        """Create decision to execute workflow."""
        return Decision(
            decision_type=DecisionType.EXECUTE_WORKFLOW,
            reason=f"All requirements met for {intent}",
            execution_mode=execution_mode,
            requires_confirmation=False,
            metadata={"intent": intent, "execution_mode": execution_mode},
        )

    def _determine_execution_mode(self, intent: ConversationIntent) -> ExecutionMode:
        """Determine appropriate execution mode based on intent."""
        # Most workflows use sequential execution
        # Parallel execution would be determined by future workflow definitions
        return ExecutionMode.SEQUENTIAL


__all__ = [
    "Decision",
    "DecisionType",
    "ExecutionMode",
    "DecisionEngine",
]
