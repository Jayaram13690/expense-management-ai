import sys

sys.path.insert(0, ".")

from agents.policy_agent import PolicyAgent
from scripts.runtime.common import RuntimeScenario, run_scenario

agent = PolicyAgent()

scenarios = [
    RuntimeScenario(
        "Policy Lookup",
        "Retrieve reimbursement policy for employee grade G5.",
        "get_expense_policy",
    ),
    RuntimeScenario(
        "Hotel Limit",
        "Retrieve hotel reimbursement limit for grade G5.",
        "get_expense_category",
    ),
    RuntimeScenario(
        "Meals Limit",
        "What is the meals reimbursement limit for G5 employees?",
        "get_expense_category",
    ),
]

for scenario in scenarios:
    run_scenario(agent, scenario)
