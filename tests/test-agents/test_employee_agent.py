import sys

# Add the src directory to the Python path
sys.path.insert(0, ".")

from agents.employee_agent import EmployeeAgent

agent = EmployeeAgent()

queries = [
    "Retrieve employee EMP0006 details.",
]

for q in queries:
    print("=" * 80)
    print(q)

    result = agent.invoke(q)
