import sys

sys.path.insert(0, ".")

from agents.employee_agent import EmployeeAgent
from scripts.runtime.common import RuntimeScenario, run_scenario

agent = EmployeeAgent()

scenarios = [
    RuntimeScenario(
        "Employee Details",
        "Retrieve employee EMP0006 details.",
        "get_employee_details",
    ),
    RuntimeScenario(
        "Employee Profile",
        "Who is employee EMP0006?",
        "get_employee_details",
    ),
    RuntimeScenario(
        "Claim History",
        "List all expense claims for employee EMP0006.",
        "list_employee_claims",
    ),
]

for scenario in scenarios:
    run_scenario(agent, scenario)
