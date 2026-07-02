"""
Agent Request Builder.

This module provides the AgentRequestBuilder that transforms workflow context into
meaningful runtime business requests for specialized agents. The builder is a pure
transformation component with no business logic or external dependencies.

Design Principles:
------------------
- Pure transformation - no business logic
- No external dependencies (agents, services, repositories, tools)
- No validation or calculation
- No decision making
- No error handling beyond basic input validation
- Input: WorkflowStep, WorkflowContext, Previous Results
- Output: str (runtime business request)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coordinator.workflow import WorkflowStep


class AgentRequestBuilder:
    # Dispatch table for stage-specific builders
    _BUILDERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], str]] = {}
    """
    Transforms workflow context into runtime business requests for agents.

    This class is responsible for building meaningful business requests that
    specialized agents can understand and process. It acts as a pure transformation
    layer between the workflow execution context and agent invocation.

    Design Principles:
        - Pure transformation component
        - No business logic or domain knowledge
        - No external dependencies
        - No validation or calculation
        - No agent/tool/service/repository imports
        - No error handling beyond basic input validation
    """

    @staticmethod
    def build(
        workflow_step: WorkflowStep,
        workflow_context: dict[str, Any],
        previous_results: dict[str, Any],
    ) -> str:
        """
        Build a runtime business request for the specified workflow step.

        Args:
            workflow_step: The workflow step being executed
            workflow_context: Current workflow execution context
            previous_results: Results from previous workflow stages

        Returns:
            str: Runtime business request suitable for agent invocation

        Raises:
            ValueError: If required inputs are missing or invalid
        """
        # Validate inputs
        if workflow_step is None:
            raise ValueError("workflow_step cannot be None")
        if workflow_context is None:
            raise ValueError("workflow_context cannot be None")
        if previous_results is None:
            raise ValueError("previous_results cannot be None")

        # Use dispatch table to find the appropriate builder
        builder = AgentRequestBuilder._BUILDERS.get(workflow_step.stage_name)
        if builder is not None:
            return builder(workflow_context, previous_results)
        else:
            # For unknown stages, build a generic request
            return _build_generic_request(workflow_step)

    # Dispatch table for stage-specific builders
    # (defined after functions to avoid circular dependency)


def _build_employee_retrieval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for employee retrieval."""
    return f"Retrieve employee details.\n\nEmployee Information:\n{workflow_context}"


def _build_policy_eligibility_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for policy eligibility lookup."""
    return (
        f"Retrieve the applicable expense policy.\n\n"
        f"Employee Information:\n"
        f"{previous_results.get('employee_retrieval', {})}\n\n"
        f"Expense Category:\n"
        f"{workflow_context.get('expense_category', '')}"
    )


def _build_category_limit_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for category limit lookup."""
    return (
        f"Retrieve the expense category limits.\n\n"
        f"Expense Category:\n"
        f"{workflow_context.get('expense_category', '')}"
    )


def _build_expense_preview_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for expense preview."""
    return (
        f"Generate an expense claim preview.\n\n"
        f"Employee Information:\n"
        f"{previous_results.get('employee_retrieval', {})}\n\n"
        f"Policy Information:\n"
        f"{previous_results.get('policy_eligibility_lookup', {})}\n\n"
        f"Expense Items:\n"
        f"{workflow_context.get('expense_items', [])}"
    )


def _build_expense_submission_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for expense submission."""
    return "Submit this approved expense claim."


def _build_receipt_upload_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for receipt upload."""
    return "Upload and associate this receipt with the expense claim."


def _build_approval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for approval."""
    return "Approve or reject this expense claim."


def _build_policy_retrieval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for policy retrieval."""
    return f"Retrieve expense policy details.\n\nPolicy Information:\n{workflow_context}"


def _build_expense_retrieval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for expense retrieval."""
    return (
        f"Retrieve expense claim details.\n\n"
        f"Employee Information:\n"
        f"{previous_results.get('employee_retrieval', {})}\n\n"
        f"Expense Information:\n"
        f"{workflow_context}"
    )


def _build_receipt_validation_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for receipt validation."""
    return f"Validate receipt for upload.\n\nReceipt Information:\n{workflow_context}"


def _build_receipt_processing_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for receipt processing."""
    return (
        f"Process validated receipt.\n\n"
        f"Receipt Information:\n"
        f"{workflow_context}\n\n"
        f"Validation Results:\n"
        f"{previous_results.get('receipt_validation', {})}"
    )


def _build_receipt_association_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for receipt association."""
    return (
        f"Associate processed receipt with expense claim.\n\n"
        f"Receipt Information:\n"
        f"{previous_results.get('receipt_processing', {})}"
    )


def _build_approval_validation_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for approval validation."""
    return f"Validate expense claim for approval.\n\nExpense Claim Information:\n{workflow_context}"


def _build_manager_approval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for manager approval."""
    return (
        f"Request manager approval for expense claim.\n\n"
        f"Expense Claim Information:\n"
        f"{workflow_context}\n\n"
        f"Validation Results:\n"
        f"{previous_results.get('approval_validation', {})}"
    )


def _build_approval_notification_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for approval notification."""
    return (
        f"Send approval notification.\n\n"
        f"Approval Decision:\n"
        f"{previous_results.get('manager_approval', {})}"
    )


def _build_rejection_validation_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for rejection validation."""
    return (
        f"Validate expense claim for rejection.\n\nExpense Claim Information:\n{workflow_context}"
    )


def _build_manager_rejection_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for manager rejection."""
    return (
        f"Request manager rejection for expense claim.\n\n"
        f"Expense Claim Information:\n"
        f"{workflow_context}\n\n"
        f"Validation Results:\n"
        f"{previous_results.get('rejection_validation', {})}"
    )


def _build_rejection_notification_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for rejection notification."""
    return (
        f"Send rejection notification.\n\n"
        f"Rejection Decision:\n"
        f"{previous_results.get('manager_rejection', {})}"
    )


def _build_claims_listing_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for claims listing."""
    return (
        f"List employee expense claims.\n\n"
        f"Employee Information:\n"
        f"{previous_results.get('employee_retrieval', {})}"
    )


def _build_category_retrieval_request(
    workflow_context: dict[str, Any],
    previous_results: dict[str, Any],
) -> str:
    """Build request for category retrieval."""
    return f"Retrieve expense category details.\n\nCategory Information:\n{workflow_context}"


def _build_generic_request(workflow_step: WorkflowStep) -> str:
    """Build a generic request for unknown stages."""
    return (
        f"Execute workflow stage: {workflow_step.stage_name}.\n\nAgent: {workflow_step.agent_name}"
    )


# Populate the dispatch table
AgentRequestBuilder._BUILDERS.update(
    {
        "employee_retrieval": _build_employee_retrieval_request,
        "policy_eligibility_lookup": _build_policy_eligibility_request,
        "category_limit_lookup": _build_category_limit_request,
        "expense_preview": _build_expense_preview_request,
        "expense_submission": _build_expense_submission_request,
        "receipt_upload": _build_receipt_upload_request,
        "approval": _build_approval_request,
        "policy_retrieval": _build_policy_retrieval_request,
        "expense_retrieval": _build_expense_retrieval_request,
        "receipt_validation": _build_receipt_validation_request,
        "receipt_processing": _build_receipt_processing_request,
        "receipt_association": _build_receipt_association_request,
        "approval_validation": _build_approval_validation_request,
        "manager_approval": _build_manager_approval_request,
        "approval_notification": _build_approval_notification_request,
        "rejection_validation": _build_rejection_validation_request,
        "manager_rejection": _build_manager_rejection_request,
        "rejection_notification": _build_rejection_notification_request,
        "claims_listing": _build_claims_listing_request,
        "category_retrieval": _build_category_retrieval_request,
    }
)


__all__ = ["AgentRequestBuilder"]
