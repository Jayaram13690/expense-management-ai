import sys

sys.path.insert(0, ".")

from agents.expense_agent import ExpenseAgent
from scripts.runtime.common import RuntimeScenario, run_scenario

agent = ExpenseAgent()

scenarios = [
    RuntimeScenario(
        "Expense Preview",
        """
Generate reimbursement preview.

Employee: EMP0006

Expenses

Hotel 6500 INR

Taxi 800 INR

Meals 1200 INR
""",
        "preview_expense_claim",
    ),
    RuntimeScenario(
        "Expense Submission",
        """
Submit expense claim.

Employee: EMP0006

Hotel 6500 INR

Taxi 800 INR

Meals 1200 INR
""",
        "submit_expense_claim",
    ),
]

for scenario in scenarios:
    run_scenario(agent, scenario)
