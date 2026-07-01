"""
PolicyAgent for handling policy and category lookup operations.

This module implements the PolicyAgent that inherits from BaseAgent and
is responsible for policy information retrieval and expense category lookup.

The PolicyAgent uses ONLY the following Strands tools:
- get_policy: Retrieve expense policy by category and employee grade
- get_expense_category: Retrieve expense category details by category code

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
from prompts.policy_prompt import POLICY_AGENT_SYSTEM_PROMPT
from tools.policy_tools import get_expense_category, get_policy


class PolicyAgent(BaseAgent):
    """
    PolicyAgent for handling policy and category lookup operations.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for policy information retrieval.

    Responsibilities:
        - Retrieve expense policies by category and employee grade
        - Retrieve expense category details by category code
        - Provide policy information including reimbursement limits
        - Provide category requirements and configurations

    Tools:
        - get_policy: Retrieve policy details by category and employee grade
        - get_expense_category: Retrieve category details by category code

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the PolicyAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=POLICY_AGENT_SYSTEM_PROMPT,
            tools=[get_policy, get_expense_category],
            name="PolicyAgent",
            description="Handles policy lookup.",
        )
