"""
ApprovalAgent for handling claim approval workflows.

This module implements the ApprovalAgent that inherits from BaseAgent and
is responsible for expense claim approval operations including approving,
rejecting, and managing approval queues.

The ApprovalAgent uses ONLY the following Strands tools:
- approve_claim: Approve expense claims
- reject_claim: Reject expense claims with reasons
- list_pending_claims: List all claims awaiting approval
- list_manager_queue: List claims for specific managers

Design Principles:
------------------
- Inherits from BaseAgent (no direct Strands Agent usage)
- Uses only specified tools (no service/repository access)
- Contains no business logic
- Contains no domain-specific knowledge
- Pure delegation to tools
- Clear separation of concerns
"""

from collections.abc import Mapping
from typing import Any

from agents.base_agent import BaseAgent
from prompts.approval_prompt import APPROVAL_AGENT_SYSTEM_PROMPT
from tools.approval_tools import (
    approve_claim,
    get_approval_history,
    get_approval_status,
    list_manager_queue,
    list_pending_claims,
    reject_claim,
)


class ApprovalAgent(BaseAgent):
    """
    ApprovalAgent for handling claim approval workflows.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for expense claim approval management.

    Responsibilities:
        - Approve expense claims that meet requirements
        - Reject expense claims with valid reasons
        - List all pending claims awaiting approval
        - List claims assigned to specific managers
        - Retrieve pending approvals
        - Retrieve approval status
        - Retrieve approval history
        - Manage approval queues

    Tools:
        - approve_claim: Approve claims that meet requirements
        - reject_claim: Reject claims with reasons
        - list_pending_claims: Get all claims awaiting approval
        - list_manager_queue: Get claims for specific managers
        - get_approval_status: Retrieve approval status for a claim
        - get_approval_history: Retrieve approval history for an employee

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the ApprovalAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=APPROVAL_AGENT_SYSTEM_PROMPT,
            tools=[
                approve_claim,
                reject_claim,
                list_pending_claims,
                list_manager_queue,
                get_approval_status,
                get_approval_history,
            ],
            name="ApprovalAgent",
            description="Handles approval workflows.",
        )

    def get_approval_result(self, claim_id: str) -> dict[str, Any]:
        """Retrieve approval status for orchestration."""

        result = get_approval_status(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}
