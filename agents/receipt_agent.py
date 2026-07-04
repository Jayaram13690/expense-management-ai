"""
ReceiptAgent for handling business document generation.

This module implements the ReceiptAgent that inherits from BaseAgent and
is responsible for generating business documents from expense claims.

The ReceiptAgent uses ONLY the following Strands tools:
- upload_receipt: Upload receipt documents (legacy)
- get_receipt_status: Retrieve receipt processing status (legacy)
- generate_expense_claim_summary: Generate expense claim summary
- generate_reimbursement_summary: Generate reimbursement summary
- generate_policy_application_summary: Generate policy application summary
- generate_expense_breakdown: Generate detailed expense breakdown
- generate_variance_report: Generate variance report

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
from prompts.receipt_prompt import RECEIPT_AGENT_SYSTEM_PROMPT
from tools.receipt_tools import (
    generate_expense_breakdown,
    generate_expense_claim_summary,
    generate_policy_application_summary,
    generate_reimbursement_summary,
    generate_variance_report,
    get_receipt_status,
    upload_receipt,
)


class ReceiptAgent(BaseAgent):
    """
    ReceiptAgent for handling business document generation.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for generating business documents from expense claims.

    Responsibilities:
        - Generate expense claim summary documents
        - Generate reimbursement summary documents
        - Generate policy application summary documents
        - Generate detailed expense breakdown documents
        - Generate variance report documents
        - Upload receipt documents (legacy functionality)
        - Retrieve receipt processing status (legacy functionality)

    Tools:
        - generate_expense_claim_summary: Generate expense claim summary
        - generate_reimbursement_summary: Generate reimbursement summary
        - generate_policy_application_summary: Generate policy application summary
        - generate_expense_breakdown: Generate detailed expense breakdown
        - generate_variance_report: Generate variance report
        - upload_receipt: Upload receipt documents (legacy)
        - get_receipt_status: Retrieve receipt status (legacy)

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the ReceiptAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=RECEIPT_AGENT_SYSTEM_PROMPT,
            tools=[
                generate_expense_claim_summary,
                generate_reimbursement_summary,
                generate_policy_application_summary,
                generate_expense_breakdown,
                generate_variance_report,
                upload_receipt,
                get_receipt_status,
            ],
            name="ReceiptAgent",
            description="Handles business document generation.",
        )

    def generate_receipt_result(self, claim_id: str) -> dict[str, Any]:
        """Generate the final acknowledgement payload for orchestration."""

        result = generate_reimbursement_summary(claim_id)
        if hasattr(result, "model_dump") and callable(result.model_dump):
            return result.model_dump()
        if isinstance(result, Mapping):
            return dict(result)
        return {"value": result}
