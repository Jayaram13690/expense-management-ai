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

from __future__ import annotations

from typing import Any

from agents.base_agent import BaseAgent
from prompts.policy_prompt import POLICY_AGENT_SYSTEM_PROMPT
from tools.policy_tools import (
    check_employee_eligibility,
    get_category_limits,
    get_expense_category,
    get_policy_by_identifier,
    get_reimbursement_rules,
)


class PolicyAgent(BaseAgent):
    """
    PolicyAgent for handling policy and category lookup operations.

    This agent inherits from BaseAgent and is configured with the specific
    system prompt for policy information retrieval.
    """

    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            model=model,
            system_prompt=POLICY_AGENT_SYSTEM_PROMPT,
            tools=[
                get_policy_by_identifier,
                get_expense_category,
                check_employee_eligibility,
                get_category_limits,
                get_reimbursement_rules,
            ],
            name="PolicyAgent",
            description="Handles policy lookup.",
        )

    def check_employee_eligibility(self, category_identifier: str, employee_grade: str) -> bool:
        return bool(
            check_employee_eligibility(
                category_identifier=category_identifier,
                employee_grade=employee_grade,
            )
        )

    def get_category_limits(self, category_identifier: str, employee_grade: str) -> dict[str, Any]:
        limits = get_category_limits(
            category_identifier=category_identifier,
            employee_grade=employee_grade,
        )
        if hasattr(limits, "model_dump") and callable(limits.model_dump):
            limits = limits.model_dump()
        if isinstance(limits, dict):
            return limits
        return {"value": limits}
