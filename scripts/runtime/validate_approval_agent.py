import sys

sys.path.insert(0, ".")

from agents.approval_agent import ApprovalAgent
from scripts.runtime.common import RuntimeScenario, run_scenario

agent = ApprovalAgent()

scenarios = [
    RuntimeScenario(
        "Approve Claim",
        "Approve expense claim CLM0001.",
        "approve_claim",
    ),
    RuntimeScenario(
        "Reject Claim",
        "Reject expense claim CLM0001 because receipt is missing.",
        "reject_claim",
    ),
]

for scenario in scenarios:
    run_scenario(agent, scenario)
