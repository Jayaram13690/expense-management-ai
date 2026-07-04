# import sys
# sys.path.insert(0, ".")

from agents.approval_agent import ApprovalAgent

agent = ApprovalAgent()

queries = [
    "List pending approvals.",
    "Retrieve approval status for claim CLM114558386555.",
    """Approve claim CLM114558386555.
    Approver ID: EMP0002
    Approver Name: Rahul Sharma
    Comments: Approved after validating travel expenses.
    """,
    "Retrieve approval status for claim CLM114558386555.",
    "List pending approvals.",
    """Reject claim CLM114558386555.
    Approver ID: EMP0002
    Approver Name: Rahul Sharma
    Comments: Approved after validating travel expenses.
    """,
    "Retrieve approval status for claim CLM114558386555.",
]

for q in queries:
    print("=" * 80)

    print(q)

    result = agent.invoke(q)

    # print(result)
