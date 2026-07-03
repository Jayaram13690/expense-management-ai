import sys
sys.path.insert(0, ".")

from agents.expense_agent import ExpenseAgent

agent = ExpenseAgent()

queries = [
    """
Preview an expense claim.

Employee ID: EMP0006

Trip Name: Client Meeting Hyderabad
Business Purpose: Attended customer meetings and project discussions with the client.
Destination: Hyderabad
Trip Start Date: 2026-06-20
Trip End Date: 2026-06-22

Expense Items:
1. Hotel
   Amount: 6000
   Date: 2026-06-20
   Category: HOTEL

2. Taxi
   Amount: 900
   Date: 2026-06-21
   Category: TAXI
""",

    """
Submit an expense claim.

Employee ID: EMP0006

Trip Name: Client Meeting Hyderabad
Business Purpose: Attended customer meetings and project discussions with the client.
Destination: Hyderabad
Trip Start Date: 2026-06-20
Trip End Date: 2026-06-22

Expense Items:
1. Hotel
   Amount: 6000
   Date: 2026-06-20
   Category: HOTEL

2. Taxi
   Amount: 900
   Date: 2026-06-21
   Category: TAXI
"""
]

for query in queries:
    print("=" * 80)
    print(query)

    response = agent.invoke(query)