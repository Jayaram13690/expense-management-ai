"""
EmployeeAgent for handling employee-related operations.

This module implements the EmployeeAgent that inherits from BaseAgent and
is responsible for employee information lookup and claim history retrieval.

The EmployeeAgent uses ONLY the following Strands tools:
- get_employee_details: Retrieve complete employee information
- list_employee_claims: Get an employee's expense claim history

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
from prompts.employee_prompt import EMPLOYEE_AGENT_SYSTEM_PROMPT
from tools.employee_tools import (
    get_employee_department,
    get_employee_details,
    get_employee_grade,
    get_employee_manager,
    list_employee_claims,
)


class EmployeeAgent(BaseAgent):
    """
    EmployeeAgent for handling employee-related operations.

    This agent inherits from BaseAgent and is configured with the specific
    tools and system prompt for employee data retrieval and claim history.

    Responsibilities:
        - Retrieve employee details by employee ID
        - Retrieve employee grade
        - Retrieve employee department
        - Retrieve employee manager
        - List expense claims submitted by an employee
        - Provide employee claim history information

    Tools:
        - get_employee_details: Retrieve complete employee information
        - get_employee_grade: Retrieve employee grade
        - get_employee_department: Retrieve employee department
        - get_employee_manager: Retrieve employee manager
        - list_employee_claims: Get employee's expense claim history

    Attributes:
        Inherits all attributes from BaseAgent
    """

    def __init__(self, model: str | None = None) -> None:
        """
        Initialize the EmployeeAgent with specific tools and system prompt.

        Args:
            model: Optional model specification for the agent.
                If None, uses the default model from BaseAgent.

        Raises:
            ValueError: If agent name contains path separators.
        """
        super().__init__(
            model=model,
            system_prompt=EMPLOYEE_AGENT_SYSTEM_PROMPT,
            tools=[
                get_employee_details,
                get_employee_grade,
                get_employee_department,
                get_employee_manager,
                list_employee_claims,
            ],
            name="EmployeeAgent",
            description="Handles employee information retrieval.",
        )
