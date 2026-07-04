import sys
from collections.abc import Mapping

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
    # print("STATE:", response.get("state"))
    # print("PLAN :", response.get("plan"))
    print("\nASSISTANT:\n")
    print(_extract_assistant_text(response))
    print("=" * 80)


def _extract_assistant_text(response):
    if isinstance(response, Mapping):
        message = response.get("assistant_message")
        if message is not None:
            return message
        if response.get("response") is not None:
            return response["response"]
        return response

    message = getattr(response, "message", None)
    if isinstance(message, str):
        return message
    if isinstance(message, Mapping):
        for key in ("assistant_message", "content", "text", "response"):
            value = message.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                parts = []
                for item in value:
                    if isinstance(item, Mapping):
                        text = item.get("text") or item.get("content")
                        if isinstance(text, str):
                            parts.append(text)
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "\n".join(parts)
    if hasattr(response, "text") and isinstance(response.text, str):
        return response.text
    return str(response)


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
    user_input = input("\nYou : ")

    if user_input.lower() == "exit":
        break

    response = coordinator.route_message(user_input)

    print_response(response)
