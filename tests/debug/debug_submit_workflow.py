
import sys
sys.path.insert(0, '.')

from agents.employee_agent import EmployeeAgent
from agents.policy_agent import PolicyAgent
from agents.expense_agent import ExpenseAgent
from agents.receipt_agent import ReceiptAgent
from agents.approval_agent import ApprovalAgent

from coordinator.coordinator import Coordinator
from coordinator.decision import Decision, DecisionType
from coordinator.executor import ExecutionMode
from conversation.intents import ConversationIntent


def wrap_agent(agent):
    original = agent.invoke

    def wrapper(prompt, **kwargs):
        print("\n" + "=" * 80)
        print(f"[AGENT INVOKED] {agent.agent_name}")
        print("- Prompt -")
        print(prompt)
        print("=" * 80)

        result = original(prompt, **kwargs)

        print(f"[AGENT COMPLETED] {agent.agent_name}")
        print("=" * 80 + "\n")

        return result

    agent.invoke = wrapper


def main():

    employee = EmployeeAgent()
    policy = PolicyAgent()
    expense = ExpenseAgent()
    receipt = ReceiptAgent()
    approval = ApprovalAgent()

    wrap_agent(employee)
    wrap_agent(policy)
    wrap_agent(expense)
    wrap_agent(receipt)
    wrap_agent(approval)

    coordinator = Coordinator(
        expense_agent=expense,
        employee_agent=employee,
        policy_agent=policy,
        receipt_agent=receipt,
        approval_agent=approval,
    )

    decision = Decision(
        decision_type=DecisionType.EXECUTE_WORKFLOW,
        execution_mode=ExecutionMode.SEQUENTIAL,
    )

    # Start conversation and collect required fields
    coordinator.start_conversation(ConversationIntent.SUBMIT_EXPENSE_CLAIM)
    coordinator.collect_field("employee_id", "EMP0006")
    coordinator.collect_field("trip_name", "AWS Summit")
    coordinator.collect_field("business_purpose", "AWS Learning")
    coordinator.collect_field("destination", "Bangalore")
    coordinator.collect_field("trip_start_date", "2026-07-01")
    coordinator.collect_field("trip_end_date", "2026-07-03")
    coordinator.collect_field("expense_items", [
        {
            "category": "HOTEL",
            "amount": 6500,
        },
        {
            "category": "TAXI",
            "amount": 800,
        },
    ])
    
    result = coordinator.execute_workflow(decision=decision)

    print(result)


if __name__ == "__main__":
    main()