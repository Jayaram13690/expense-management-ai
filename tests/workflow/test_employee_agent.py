import sys

# Add the src directory to the Python path
sys.path.insert(0, '.')

from agents.employee_agent import EmployeeAgent

agent = EmployeeAgent()

queries = [
    "Retrieve employee EMP0006 details.",
    "What is the grade of employee EMP0006?",
    "Which department does employee EMP0006 belong to?",
    "Who is the manager of employee EMP0006?",
    "List expense claims submitted by employee EMP0006."
]

for q in queries:

    print("=" * 80)
    print(q)

    result = agent.invoke(q)

    print(result)