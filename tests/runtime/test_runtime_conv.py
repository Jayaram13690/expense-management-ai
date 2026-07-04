import sys

sys.path.insert(0, ".")

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from conversation.orchestrator import ConversationOrchestrator


def print_response(response):
    print("\n" + "=" * 80)
    print("STATE:", response.get("state"))
    print("PLAN :", response.get("plan"))
    print("\nASSISTANT:\n")
    print(response.get("assistant_message"))
    print("=" * 80)


employee_agent = EmployeeAgent()
policy_agent = PolicyAgent()
expense_agent = ExpenseAgent()
approval_agent = ApprovalAgent()
receipt_agent = ReceiptAgent()

orchestrator = ConversationOrchestrator(
    employee_agent=employee_agent,
    policy_agent=policy_agent,
    expense_agent=expense_agent,
    approval_agent=approval_agent,
    receipt_agent=receipt_agent,
)

coordinator = CoordinatorAgent(
    employee_agent=employee_agent,
    policy_agent=policy_agent,
    expense_agent=expense_agent,
    approval_agent=approval_agent,
    receipt_agent=receipt_agent,
    conversation_orchestrator=orchestrator,
)

print("\nExpense Management AI")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You : ")

    if user_input.lower() == "exit":
        break

    response = coordinator.route_message(user_input)

    print_response(response)
