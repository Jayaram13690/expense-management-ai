import sys

from agents.receipt_agent import ReceiptAgent

sys.path.insert(0, ".")

agent = ReceiptAgent()

queries = [
    "Generate Expense Claim Summary for claim CLM114558386555",
    "Generate Reimbursement Summary for claim CLM114558386555",
    "Generate Expense Breakdown for claim CLM114558386555",
    "Generate Variance Report for claim CLM114558386555",
]

for q in queries:
    print("=" * 80)

    print(q)

    result = agent.invoke(q)
