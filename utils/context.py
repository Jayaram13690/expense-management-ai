"""
Workflow Context Management.

This module provides thread-safe context management for workflow execution.
It uses ContextVar to store workflow-specific context that can be accessed
throughout the call stack without explicit parameter passing.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass
class WorkflowContextData:
    """Data class to hold workflow context information.

    This class provides a structured way to store and access workflow-related
    context data. All fields are optional to support partial context initialization.

    Attributes:
        workflow_id: Unique identifier for the workflow instance
        request_id: Unique identifier for the request
        employee_id: Identifier for the employee associated with the workflow
        claim_id: Identifier for the claim being processed
        agent_name: Name of the agent executing the workflow
        additional_data: Dictionary for any additional context data
    """

    workflow_id: str | None = None
    request_id: str | None = None
    employee_id: str | None = None
    claim_id: str | None = None
    agent_name: str | None = None
    additional_data: dict[str, Any] | None = None


# Thread-local context variable
_workflow_context_var: ContextVar[WorkflowContextData | None] = ContextVar(
    "workflow_context", default=None
)


@contextmanager
def workflow_context(
    workflow_id: str | None = None,
    request_id: str | None = None,
    employee_id: str | None = None,
    claim_id: str | None = None,
    agent_name: str | None = None,
    **kwargs: Any,
) -> Generator[WorkflowContextData]:
    """Context manager for workflow context.

    This context manager establishes a workflow context that can be accessed
    throughout the call stack. It automatically cleans up the context when
    exiting the context block.

    Args:
        workflow_id: Unique identifier for the workflow instance
        request_id: Unique identifier for the request
        employee_id: Identifier for the employee associated with the workflow
        claim_id: Identifier for the claim being processed
        agent_name: Name of the agent executing the workflow
        **kwargs: Additional context data to be stored

    Yields:
        The workflow context data object

    Example:
        >>> with workflow_context(
        ...     workflow_id="wf-123",
        ...     request_id="req-456",
        ...     employee_id="emp-789"
        ... ) as context:
        ...     # Context is available throughout this block
        ...     logger.info(f"Processing workflow {context.workflow_id}")
    """
    # Create context data
    context_data = WorkflowContextData(
        workflow_id=workflow_id,
        request_id=request_id,
        employee_id=employee_id,
        claim_id=claim_id,
        agent_name=agent_name,
        additional_data=kwargs if kwargs else None,
    )

    # Set the context variable
    token = _workflow_context_var.set(context_data)

    try:
        yield context_data
    finally:
        # Reset to default when exiting context
        _workflow_context_var.reset(token)


def get_current_workflow_context() -> WorkflowContextData:
    """Get the current workflow context.

    Retrieves the workflow context data from the current execution context.
    Returns an empty WorkflowContextData if no context is set.

    Returns:
        The current workflow context data

    Example:
        >>> context = get_current_workflow_context()
        >>> print(f"Current workflow: {context.workflow_id}")
    """
    ctx = _workflow_context_var.get()
    if ctx is None:
        return WorkflowContextData()
    return ctx


def get_workflow_id() -> str | None:
    """Get the current workflow ID from context.

    Returns:
        The workflow ID if set, None otherwise
    """
    return get_current_workflow_context().workflow_id


def get_request_id() -> str | None:
    """Get the current request ID from context.

    Returns:
        The request ID if set, None otherwise
    """
    return get_current_workflow_context().request_id


def get_employee_id() -> str | None:
    """Get the current employee ID from context.

    Returns:
        The employee ID if set, None otherwise
    """
    return get_current_workflow_context().employee_id


def get_claim_id() -> str | None:
    """Get the current claim ID from context.

    Returns:
        The claim ID if set, None otherwise
    """
    return get_current_workflow_context().claim_id


def get_agent_name() -> str | None:
    """Get the current agent name from context.

    Returns:
        The agent name if set, None otherwise
    """
    return get_current_workflow_context().agent_name


def get_additional_context_data() -> dict[str, Any] | None:
    """Get additional context data.

    Returns:
        Dictionary of additional context data if set, None otherwise
    """
    return get_current_workflow_context().additional_data


__all__ = [
    "workflow_context",
    "get_current_workflow_context",
    "get_workflow_id",
    "get_request_id",
    "get_employee_id",
    "get_claim_id",
    "get_agent_name",
    "get_additional_context_data",
    "WorkflowContextData",
]
