"""
Coordinator Infrastructure.

This module provides the Coordinator infrastructure for the Enterprise AI Travel
Expense Management System. The Coordinator serves as the single entry point
into the application.

Design Principles:
------------------
- Single entry point for all user interactions
- Infrastructure only - no workflow execution
- No business logic
- No direct service/repository/tool access
- Uses only specialized agents and conversation layer
- Dependency injection for all agent dependencies
- Clean separation of concerns
"""

from __future__ import annotations

from typing import Any

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from conversation.intents import ConversationIntent
from coordinator.builders import CoordinatorRequestBuilder
from coordinator.conversation import ConversationManager
from coordinator.decision import Decision, DecisionEngine, DecisionType
from coordinator.executor import WorkflowExecutor
from coordinator.state import WorkflowState
from coordinator.workflow import get_workflow_definition


class Coordinator:
    """
    Coordinator Infrastructure.

    The Coordinator is the single entry point into the application. It owns
    references to all specialized agents and provides a clean public API for
    workflow orchestration.

    Responsibilities:
        - Application entry point
        - Own references to specialized agents
        - Expose clean public API
        - Initialize dependencies

    Attributes:
        expense_agent: Reference to ExpenseAgent
        employee_agent: Reference to EmployeeAgent
        policy_agent: Reference to PolicyAgent
        receipt_agent: Reference to ReceiptAgent
        approval_agent: Reference to ApprovalAgent
        _current_state: Current workflow state
        _request_builder: Request builder for DTO construction
    """

    def __init__(
        self,
        expense_agent: ExpenseAgent,
        employee_agent: EmployeeAgent,
        policy_agent: PolicyAgent,
        receipt_agent: ReceiptAgent,
        approval_agent: ApprovalAgent,
    ) -> None:
        """
        Initialize the Coordinator with all specialized agents.

        Args:
            expense_agent: ExpenseAgent instance for expense operations
            employee_agent: EmployeeAgent instance for employee operations
            policy_agent: PolicyAgent instance for policy operations
            receipt_agent: ReceiptAgent instance for receipt operations
            approval_agent: ApprovalAgent instance for approval operations

        Raises:
            ValueError: If any agent is None
        """
        if None in (expense_agent, employee_agent, policy_agent, receipt_agent, approval_agent):
            raise ValueError("All specialized agents must be provided")

        self.expense_agent = expense_agent
        self.employee_agent = employee_agent
        self.policy_agent = policy_agent
        self.receipt_agent = receipt_agent
        self.approval_agent = approval_agent

        # Initialize infrastructure components
        self._current_state: WorkflowState = WorkflowState.STARTED
        self._request_builder = CoordinatorRequestBuilder()
        self._conversation_manager = ConversationManager(request_builder=self._request_builder)
        self._decision_engine = DecisionEngine()
        self._workflow_executor = WorkflowExecutor(
            expense_agent=expense_agent,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            receipt_agent=receipt_agent,
            approval_agent=approval_agent,
        )

    @property
    def current_state(self) -> WorkflowState:
        """Get the current workflow state."""
        return self._current_state

    def shutdown(self) -> None:
        """Shutdown the Coordinator and clean up resources."""
        self._current_state = WorkflowState.CANCELLED

    def status(self) -> dict[str, Any]:
        """Get the current status of the Coordinator."""
        return {
            "state": self._current_state,
            "agents_initialized": {
                "expense_agent": self.expense_agent is not None,
                "employee_agent": self.employee_agent is not None,
                "policy_agent": self.policy_agent is not None,
                "receipt_agent": self.receipt_agent is not None,
                "approval_agent": self.approval_agent is not None,
            },
            "request_builder_ready": self._request_builder is not None,
            # Debugging metadata
            "current_intent": self.current_intent(),
            "missing_required_fields": self.get_missing_fields(),
            "ready_to_execute": self.is_ready_to_execute(),
        }

    def get_request_builder(self) -> CoordinatorRequestBuilder:
        """Get the request builder for DTO construction."""
        return self._request_builder

    def start_conversation(self, intent: ConversationIntent) -> None:
        """Start a conversation for the specified intent."""
        self._conversation_manager.start_conversation(intent)
        self._current_state = WorkflowState.COLLECTING_INFORMATION

    def collect_field(self, field_name: str, value: Any) -> None:
        """Collect a field value during conversation."""
        self._conversation_manager.collect_field(field_name, value)
        # self._request_builder.add_field(field_name, value)

    def get_next_prompt(self) -> str | None:
        """Get the next conversational prompt to ask the user."""
        return self._conversation_manager.get_next_prompt()

    def is_ready_to_execute(self) -> bool:
        """Check if all required information has been collected."""
        if self._conversation_manager.is_ready_to_execute():
            self._current_state = WorkflowState.READY_TO_EXECUTE
            return True
        return False

    def current_intent(self) -> ConversationIntent | None:
        """Get the current conversation intent."""
        return self._conversation_manager.current_intent()

    def current_requirements(self) -> Any | None:
        """Get the current intent requirements."""
        return self._conversation_manager.current_requirements()

    def get_decision(self) -> Decision:
        """
        Get the current decision from the Decision Engine.

        This method determines what should happen next based on the current
        conversation state, requirements, and collected information.

        Returns:
            Decision: What the Coordinator should do next
        """
        intent = self.current_intent()
        requirements = self.current_requirements()

        return self._decision_engine.decide(
            intent=intent,
            requirements=requirements,
            request_builder=self._request_builder,
            current_state=self._current_state,
        )

    def execute_workflow(self, decision: Decision) -> dict[str, Any]:
        """
        Execute a workflow based on the provided decision.

        This method determines the appropriate workflow definition based on the
        decision and delegates execution to the WorkflowExecutor.

        Args:
            decision: The decision containing workflow execution instructions

        Returns:
            Dictionary containing workflow execution results

        Raises:
            ValueError: If the decision is not executable
            RuntimeError: If workflow execution fails
        """
        # Validate that this is an executable decision
        if decision.decision_type != DecisionType.EXECUTE_WORKFLOW:
            raise ValueError(f"Cannot execute workflow for decision type: {decision.decision_type}")

        # Determine the workflow type from the current intent
        intent = self.current_intent()
        if intent is None:
            raise ValueError("No current intent set for workflow execution")

        # Get the workflow definition for this intent
        try:
            workflow_definition = get_workflow_definition(intent)
        except ValueError as e:
            raise ValueError(f"No workflow definition found for intent {intent}: {e}") from e

        # Execute the workflow using the specified execution mode
        execution_results = self._workflow_executor.execute_workflow(
            workflow_definition=workflow_definition, execution_mode=decision.execution_mode
        )

        # Update coordinator state based on execution results
        if execution_results["status"] == "completed":
            self._current_state = WorkflowState.COMPLETED
        elif execution_results["status"] == "waiting_for_confirmation":
            self._current_state = WorkflowState.WAITING_FOR_CONFIRMATION
        elif execution_results["status"] == "cancelled":
            self._current_state = WorkflowState.CANCELLED
        else:
            self._current_state = WorkflowState.FAILED

        return execution_results

    def get_missing_fields(self) -> list[str]:
        """Get list of missing required fields."""
        return self._conversation_manager.get_missing_required_fields()

    def reset(self) -> None:
        """Reset the Coordinator to initial state."""
        self._current_state = WorkflowState.STARTED
        self._request_builder.clear()
        self._conversation_manager.reset()

    def __repr__(self) -> str:
        """
        Get a string representation of the Coordinator.

        Returns:
            String representation including current state
        """
        return f"Coordinator(state='{self._current_state}')"

    def resume_workflow(self, workflow_id: str, employee_decision: bool) -> dict[str, Any]:
        """
        Resume a paused workflow from a confirmation point.

        This method allows the Coordinator to resume workflows that were paused
        at confirmation points (Human-in-the-Loop).

        Args:
            workflow_id: The ID of the paused workflow to resume
            employee_decision: True to continue workflow, False to cancel

        Returns:
            Dictionary containing workflow execution results

        Raises:
            ValueError: If workflow_id is not found or workflow is not paused
            RuntimeError: If workflow execution fails
        """
        # Update state to RESUMED during resume operation
        self._current_state = WorkflowState.EXECUTING

        # Delegate to workflow executor
        resume_results = self._workflow_executor.resume_workflow(
            workflow_id=workflow_id, employee_decision=employee_decision
        )

        # Update coordinator state based on resume results
        if resume_results["status"] == "completed":
            self._current_state = WorkflowState.COMPLETED
        elif resume_results["status"] == "cancelled":
            self._current_state = WorkflowState.CANCELLED
        elif resume_results["status"] == "failed":
            self._current_state = WorkflowState.FAILED

        return resume_results


__all__ = ["Coordinator"]
