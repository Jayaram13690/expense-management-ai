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

from agents.base_agent import BaseAgent
from prompts.expense_prompt import EXPENSE_AGENT_SYSTEM_PROMPT
from tools.expense_tools import get_claim, preview_claim, submit_claim


class ExpenseAgent(BaseAgent):
    """
    ExpenseAgent for handling expense claim operations.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for expense claim management.

    Responsibilities:
        - Preview expense claims
        - Submit new expense claims
        - Retrieve existing expense claims

    Tools:
        - preview_claim: Calculate reimbursement amounts
        - submit_claim: Persist new claims
        - get_claim: Retrieve claims by identifier

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
            tools=[preview_claim, submit_claim, get_claim],
            name="ExpenseAgent",
            description="Handles expense claim operations.",
        )
