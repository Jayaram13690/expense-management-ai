import sys

# Add the src directory to the Python path
sys.path.insert(0, ".")

from agents.policy_agent import PolicyAgent

agent = PolicyAgent()

queries = [
    "Retrieve HOTEL policy for employee grade G5.",
    "Check eligibility for employee grade G5 and category HOTEL.",
    "Retrieve category limits for MEALS and employee grade G5.",
    "Retrieve reimbursement rules for employee Grade G5 and category taxi.",
]

for q in queries:
    print("=" * 80)

    print(q)

    result = agent.invoke(q)

    print(result)
