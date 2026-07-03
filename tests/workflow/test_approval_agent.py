from agents.approval_agent import ApprovalAgent

agent = ApprovalAgent()

queries = [
    "List pending approvals.",
    "Retrieve approval status for claim CLMxxxx.",
    "Approve claim CLMxxxx.",
]

for q in queries:
    print("=" * 80)

    print(q)

    result = agent.invoke(q)

    print(result)
