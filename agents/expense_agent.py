"""
ExpenseAgent for handling expense claim operations.

This module implements the ExpenseAgent that inherits from BaseAgent and
is responsible for expense claim operations including previewing, submitting,
and retrieving claims.

The ExpenseAgent uses ONLY the following Strands tools:
- preview_claim: Calculate reimbursement preview
- submit_claim: Submit new expense claims
- get_claim: Retrieve existing expense claims

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
from models.dto.claim_preview import ClaimPreview
from models.dto.submit_claim import SubmitExpenseClaimRequest
from models.expense_claim import ExpenseClaim
from prompts.expense_prompt import EXPENSE_AGENT_SYSTEM_PROMPT
from tools.allowance_tools import (
    get_allowance_summary_tool,
    get_remaining_allowance_tool,
    validate_allowance_tool,
)
from tools.expense_tools import (
    calculate_reimbursement,
    calculate_variance,
    detect_duplicate_claims,
    get_claim,
)
from tools.expense_tools import get_claim_status as get_claim_status_tool
from tools.expense_tools import (
    preview_claim,
    submit_claim,
    validate_policy_compliance,
)


class ExpenseAgent(BaseAgent):
    """
    ExpenseAgent for handling expense claim operations.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for expense claim management.

    Responsibilities:
        - Validate expense claim
        - Validate policy compliance
        - Duplicate claim detection
        - Reimbursement calculation
        - Variance calculation
        - Expense preview
        - Submit expense claim
        - Persist claim
        - Retrieve claim
        - Retrieve claim status

    Tools:
        - preview_claim: Calculate reimbursement amounts
        - submit_claim: Persist new claims
        - get_claim: Retrieve claims by identifier
        - validate_policy_compliance: Validate policy compliance
        - detect_duplicate_claims: Detect duplicate claims
        - calculate_reimbursement: Calculate reimbursement amounts
        - calculate_variance: Calculate variance between amounts
        - get_claim_status: Retrieve detailed claim status

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the ExpenseAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=EXPENSE_AGENT_SYSTEM_PROMPT,
            tools=[
                preview_claim,
                submit_claim,
                get_claim,
                validate_policy_compliance,
                detect_duplicate_claims,
                calculate_reimbursement,
                calculate_variance,
                get_claim_status_tool,
                # Allowance tools — inserted after Variance Calculation stage
                validate_allowance_tool,
                get_remaining_allowance_tool,
                get_allowance_summary_tool,
            ],
            name="ExpenseAgent",
            description="Handles expense claim operations.",
        )

    def preview_claim_request(
        self,
        request: SubmitExpenseClaimRequest | dict[str, Any],
        *,
        employee_profile: Any | None = None,
        policy_context: Any | None = None,
    ) -> ClaimPreview:
        """Generate a claim preview directly from the expense tools."""

        normalized = self._normalize_request(request)
        return preview_claim(normalized)

    def submit_claim_request(
        self,
        request: SubmitExpenseClaimRequest | dict[str, Any],
        *,
        employee_profile: Any | None = None,
        policy_context: Any | None = None,
    ) -> ExpenseClaim:
        """Submit a claim directly from the expense tools."""

        normalized = self._normalize_request(request)
        return submit_claim(normalized)

    def get_claim_status(self, claim_id: str) -> dict[str, Any]:
        """Return claim status through the underlying tool."""

        result = get_claim_status_tool(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}

    def _normalize_request(
        self, request: SubmitExpenseClaimRequest | dict[str, Any]
    ) -> SubmitExpenseClaimRequest:
        if isinstance(request, SubmitExpenseClaimRequest):
            return request
        return SubmitExpenseClaimRequest.model_validate(request)
