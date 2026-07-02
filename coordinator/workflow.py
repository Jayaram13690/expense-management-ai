"""
Workflow Definitions.

This module defines the immutable workflow metadata for the Coordinator's Workflow Executor.
These definitions contain only metadata about workflows and steps, without containing
any execution logic or business processing.

Design Principles:
------------------
- Immutable data structures using frozen dataclasses
- Pure metadata representation - no execution logic
- Type-safe enums for workflow categories
- Comprehensive metadata for workflow orchestration
- No dependencies on services, agents, or tools
- No business logic or domain-specific knowledge
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class WorkflowType(StrEnum):
    """
    Enumeration of workflow types supported by the system.

    Each workflow type represents a specific business process that can be
    executed by the Workflow Executor.
    """

    # Expense claim workflows
    SUBMIT_EXPENSE_CLAIM = "submit_expense_claim"
    PREVIEW_EXPENSE_CLAIM = "preview_expense_claim"
    GET_EXPENSE_CLAIM = "get_expense_claim"

    # Receipt workflows
    UPLOAD_RECEIPT = "upload_receipt"
    GET_RECEIPT_STATUS = "get_receipt_status"

    # Approval workflows
    APPROVE_CLAIM = "approve_claim"
    REJECT_CLAIM = "reject_claim"

    # Employee workflows
    GET_EMPLOYEE_DETAILS = "get_employee_details"
    LIST_EMPLOYEE_CLAIMS = "list_employee_claims"

    # Policy workflows
    GET_POLICY = "get_policy"
    GET_EXPENSE_CATEGORY = "get_expense_category"


@dataclass(frozen=True)
class WorkflowStep:
    """
    Immutable metadata representing a business stage in a workflow.

    This class captures the metadata about what business stage should be executed,
    without containing any logic to perform the execution.

    Attributes:
        stage_name:
            Unique identifier for this business stage within the workflow

        agent_name:
            Name of the specialized agent that should execute this stage, or None

        execution_order:
            The order in which this stage should be executed (1-based)

        requires_confirmation:
            Whether this stage requires user confirmation before proceeding

        requires_receipt:
            Whether this stage requires receipt upload

        requires_manager:
            Whether this stage requires manager approval

        depends_on:
            Tuple of stage names that this stage depends on (for concurrent execution)

        metadata:
            Additional context and information about the stage
    """

    stage_name: str
    agent_name: str | None
    execution_order: int
    requires_confirmation: bool = False
    requires_receipt: bool = False
    requires_manager: bool = False
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, str] = None

    def __post_init__(self) -> None:
        """Ensure metadata is properly initialized."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Immutable metadata representing a complete workflow definition.

    This class captures the structure and requirements of a workflow without
    containing any logic to execute it.

    Attributes:
        workflow_type:
            The type of workflow this definition represents

        steps:
            Sequence of workflow steps that comprise this workflow

        description:
            Human-readable description of the workflow

        metadata:
            Additional context and information about the workflow
    """

    workflow_type: WorkflowType
    steps: Sequence[WorkflowStep]
    description: str
    metadata: dict[str, str] = None

    def __post_init__(self) -> None:
        """Ensure metadata is properly initialized and validate steps."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate that steps are properly ordered
        self._validate_step_ordering()

    def _validate_step_ordering(self) -> None:
        """Validate that stages have unique, sequential execution orders starting from 1."""
        execution_orders = [stage.execution_order for stage in self.steps]

        # Check that orders start from 1 and are sequential
        expected_orders = list(range(1, len(self.steps) + 1))
        if execution_orders != expected_orders:
            raise ValueError(
                f"Workflow stages must have sequential execution orders starting from 1. "
                f"Expected {expected_orders}, got {execution_orders}"
            )

        # Check for duplicate stage names
        stage_names = [stage.stage_name for stage in self.steps]
        if len(stage_names) != len(set(stage_names)):
            raise ValueError("Workflow stages must have unique names")


# Workflow Definitions
# These definitions contain only metadata about workflow structure
# They do not contain any business logic or execution code

SUBMIT_EXPENSE_CLAIM_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.SUBMIT_EXPENSE_CLAIM,
    steps=(
        WorkflowStep(
            stage_name="employee_retrieval",
            agent_name="EmployeeAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="policy_eligibility_lookup",
            agent_name="PolicyAgent",
            execution_order=2,
            requires_confirmation=False,
            depends_on=("employee_retrieval",),
        ),
        WorkflowStep(
            stage_name="category_limit_lookup",
            agent_name="PolicyAgent",
            execution_order=3,
            requires_confirmation=False,
            depends_on=("employee_retrieval",),
        ),
        WorkflowStep(
            stage_name="merge_policy_results",
            agent_name=None,
            execution_order=4,
            requires_confirmation=False,
            depends_on=(
                "policy_eligibility_lookup",
                "category_limit_lookup",
            ),
        ),
        WorkflowStep(
            stage_name="expense_preview",
            agent_name="ExpenseAgent",
            execution_order=5,
            requires_confirmation=True,
            depends_on=("merge_policy_results",),
        ),
        WorkflowStep(
            stage_name="wait_confirmation",
            agent_name=None,
            execution_order=6,
            requires_confirmation=True,
            depends_on=("expense_preview",),
        ),
        WorkflowStep(
            stage_name="expense_submission",
            agent_name="ExpenseAgent",
            execution_order=7,
            requires_confirmation=False,
            depends_on=("wait_confirmation",),
        ),
    ),
    description=(
        "Complete workflow for submitting a new expense claim with parallel policy processing"
    ),
)

PREVIEW_EXPENSE_CLAIM_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.PREVIEW_EXPENSE_CLAIM,
    steps=(
        WorkflowStep(
            stage_name="employee_retrieval",
            agent_name="EmployeeAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="policy_retrieval",
            agent_name="PolicyAgent",
            execution_order=2,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="expense_preview",
            agent_name="ExpenseAgent",
            execution_order=3,
            requires_confirmation=False,
            depends_on=(
                "employee_retrieval",
                "policy_retrieval",
            ),
        ),
    ),
    description="Workflow for previewing expense claim reimbursement with business stages",
)

GET_EXPENSE_CLAIM_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.GET_EXPENSE_CLAIM,
    steps=(
        WorkflowStep(
            stage_name="employee_retrieval",
            agent_name="EmployeeAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="expense_retrieval",
            agent_name="ExpenseAgent",
            execution_order=2,
            requires_confirmation=False,
            depends_on=("employee_retrieval",),
        ),
    ),
    description="Workflow for retrieving an existing expense claim with business stages",
)

UPLOAD_RECEIPT_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.UPLOAD_RECEIPT,
    steps=(
        WorkflowStep(
            stage_name="receipt_validation",
            agent_name="ReceiptAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="receipt_processing",
            agent_name="ReceiptAgent",
            execution_order=2,
            requires_confirmation=False,
            depends_on=("receipt_validation",),
        ),
        WorkflowStep(
            stage_name="receipt_association",
            agent_name="ReceiptAgent",
            execution_order=3,
            requires_confirmation=False,
            depends_on=("receipt_processing",),
        ),
    ),
    description="Workflow for uploading and associating receipts with claims using business stages",
)

GET_RECEIPT_STATUS_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.GET_RECEIPT_STATUS,
    steps=(
        WorkflowStep(
            stage_name="receipt_status_check",
            agent_name="ReceiptAgent",
            execution_order=1,
            requires_confirmation=False,
        ),
    ),
    description="Workflow for checking receipt processing status using business stages",
)

APPROVE_CLAIM_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.APPROVE_CLAIM,
    steps=(
        WorkflowStep(
            stage_name="approval_validation",
            agent_name="ApprovalAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="manager_approval",
            agent_name="ApprovalAgent",
            execution_order=2,
            requires_confirmation=True,
            depends_on=("approval_validation",),
        ),
        WorkflowStep(
            stage_name="approval_notification",
            agent_name="ApprovalAgent",
            execution_order=3,
            requires_confirmation=False,
            depends_on=("manager_approval",),
        ),
    ),
    description="Workflow for approving expense claims with business stages",
)

REJECT_CLAIM_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.REJECT_CLAIM,
    steps=(
        WorkflowStep(
            stage_name="rejection_validation",
            agent_name="ApprovalAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="manager_rejection",
            agent_name="ApprovalAgent",
            execution_order=2,
            requires_confirmation=True,
            depends_on=("rejection_validation",),
        ),
        WorkflowStep(
            stage_name="rejection_notification",
            agent_name="ApprovalAgent",
            execution_order=3,
            requires_confirmation=False,
            depends_on=("manager_rejection",),
        ),
    ),
    description="Workflow for rejecting expense claims with business stages",
)

GET_EMPLOYEE_DETAILS_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.GET_EMPLOYEE_DETAILS,
    steps=(
        WorkflowStep(
            stage_name="employee_retrieval",
            agent_name="EmployeeAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
    ),
    description="Workflow for retrieving employee details with business stages",
)

LIST_EMPLOYEE_CLAIMS_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.LIST_EMPLOYEE_CLAIMS,
    steps=(
        WorkflowStep(
            stage_name="employee_retrieval",
            agent_name="EmployeeAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
        WorkflowStep(
            stage_name="claims_listing",
            agent_name="EmployeeAgent",
            execution_order=2,
            requires_confirmation=False,
            depends_on=("employee_retrieval",),
        ),
    ),
    description="Workflow for listing employee claims with business stages",
)

GET_POLICY_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.GET_POLICY,
    steps=(
        WorkflowStep(
            stage_name="policy_retrieval",
            agent_name="PolicyAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
    ),
    description="Workflow for retrieving expense policy details with business stages",
)

GET_EXPENSE_CATEGORY_WORKFLOW = WorkflowDefinition(
    workflow_type=WorkflowType.GET_EXPENSE_CATEGORY,
    steps=(
        WorkflowStep(
            stage_name="category_retrieval",
            agent_name="PolicyAgent",
            execution_order=1,
            requires_confirmation=False,
            depends_on=(),
        ),
    ),
    description="Workflow for retrieving expense category details with business stages",
)


# Mapping from WorkflowType to WorkflowDefinition for easy lookup
WORKFLOW_DEFINITIONS = {
    WorkflowType.SUBMIT_EXPENSE_CLAIM: SUBMIT_EXPENSE_CLAIM_WORKFLOW,
    WorkflowType.PREVIEW_EXPENSE_CLAIM: PREVIEW_EXPENSE_CLAIM_WORKFLOW,
    WorkflowType.GET_EXPENSE_CLAIM: GET_EXPENSE_CLAIM_WORKFLOW,
    WorkflowType.UPLOAD_RECEIPT: UPLOAD_RECEIPT_WORKFLOW,
    WorkflowType.GET_RECEIPT_STATUS: GET_RECEIPT_STATUS_WORKFLOW,
    WorkflowType.APPROVE_CLAIM: APPROVE_CLAIM_WORKFLOW,
    WorkflowType.REJECT_CLAIM: REJECT_CLAIM_WORKFLOW,
    WorkflowType.GET_EMPLOYEE_DETAILS: GET_EMPLOYEE_DETAILS_WORKFLOW,
    WorkflowType.LIST_EMPLOYEE_CLAIMS: LIST_EMPLOYEE_CLAIMS_WORKFLOW,
    WorkflowType.GET_POLICY: GET_POLICY_WORKFLOW,
    WorkflowType.GET_EXPENSE_CATEGORY: GET_EXPENSE_CATEGORY_WORKFLOW,
}


def get_workflow_definition(workflow_type: WorkflowType) -> WorkflowDefinition:
    """
    Get the workflow definition for the specified workflow type.

    Args:
        workflow_type: The type of workflow to retrieve

    Returns:
        WorkflowDefinition: The workflow definition

    Raises:
        ValueError: If no workflow definition exists for the specified type
    """
    if workflow_type not in WORKFLOW_DEFINITIONS:
        raise ValueError(f"No workflow definition found for type: {workflow_type}")

    return WORKFLOW_DEFINITIONS[workflow_type]


__all__ = [
    "WorkflowType",
    "WorkflowStep",
    "WorkflowDefinition",
    "get_workflow_definition",
    # Individual workflow definitions
    "SUBMIT_EXPENSE_CLAIM_WORKFLOW",
    "PREVIEW_EXPENSE_CLAIM_WORKFLOW",
    "GET_EXPENSE_CLAIM_WORKFLOW",
    "UPLOAD_RECEIPT_WORKFLOW",
    "GET_RECEIPT_STATUS_WORKFLOW",
    "APPROVE_CLAIM_WORKFLOW",
    "REJECT_CLAIM_WORKFLOW",
    "GET_EMPLOYEE_DETAILS_WORKFLOW",
    "LIST_EMPLOYEE_CLAIMS_WORKFLOW",
    "GET_POLICY_WORKFLOW",
    "GET_EXPENSE_CATEGORY_WORKFLOW",
]
