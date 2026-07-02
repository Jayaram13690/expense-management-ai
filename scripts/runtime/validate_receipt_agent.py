import sys

sys.path.insert(0, ".")

from agents.receipt_agent import ReceiptAgent
from scripts.runtime.common import RuntimeScenario, run_scenario

agent = ReceiptAgent()

scenarios = [
    RuntimeScenario(
        "Receipt Validation",
        "Validate receipt for claim CLM0001.",
        "validate_receipt",
    ),
    RuntimeScenario(
        "Receipt Upload",
        "Upload receipt for claim CLM0001.",
        "upload_receipt",
    ),
]

for scenario in scenarios:
    run_scenario(agent, scenario)
