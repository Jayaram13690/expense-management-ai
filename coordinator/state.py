"""
Workflow State Definitions.

This module defines the workflow state enumeration for the Coordinator layer.
These states represent the progression of workflow execution without containing
any business logic or state management.

Design Principles:
------------------
- StrEnum-based for type safety and string comparison compatibility
- Represents workflow progression only (not business state)
- No helper methods or business logic
- Infrastructure for future workflow implementation
"""

from enum import StrEnum


class WorkflowState(StrEnum):
    """
    Enumeration of workflow states for the Coordinator.

    These states represent the progression of workflow execution through
    the Coordinator layer. They are used to track the current phase
    of orchestration without containing any business-specific information.

    Future workflow implementation phases will use these states to manage
    sequential execution, parallel execution, and human-in-the-loop checkpoints.
    """

    # Initial states
    STARTED = "started"
    COLLECTING_INFORMATION = "collecting_information"
    BUILDING_REQUEST = "building_request"
    READY_TO_EXECUTE = "ready_to_execute"

    # Execution states
    EXECUTING = "executing"

    # Human-in-the-loop checkpoint states
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    WAITING_FOR_RECEIPT = "waiting_for_receipt"
    WAITING_FOR_MANAGER = "waiting_for_manager"

    # Terminal states
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = ["WorkflowState"]
