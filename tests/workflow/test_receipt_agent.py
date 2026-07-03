from agents.receipt_agent import ReceiptAgent

agent = ReceiptAgent()

queries = [

    "Generate Expense Claim Summary for claim CLMxxxx",

    "Generate Reimbursement Summary for claim CLMxxxx",

    "Generate Expense Breakdown for claim CLMxxxx",

    "Generate Variance Report for claim CLMxxxx",

]

for q in queries:

    print("=" * 80)

    print(q)

    result = agent.invoke(q)

    print(result)