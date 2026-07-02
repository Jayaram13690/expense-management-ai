from unittest.mock import Mock

from coordinator.executor import WorkflowExecutor
from coordinator.workflow import SUBMIT_EXPENSE_CLAIM_WORKFLOW


def build_executor():
    agents = []

    for name in [
        "ExpenseAgent",
        "EmployeeAgent",
        "PolicyAgent",
        "ReceiptAgent",
        "ApprovalAgent",
    ]:
        agent = Mock()
        agent.agent_name = name
        agent.invoke.return_value = {"agent": name}
        agents.append(agent)

    return WorkflowExecutor(*agents), agents


def test_wait_confirmation_skipped():
    executor, agents = build_executor()

    result = executor.execute_workflow(SUBMIT_EXPENSE_CLAIM_WORKFLOW)

    assert result["results"]["wait_confirmation"] is None


def test_expense_agent_called_twice():
    executor, agents = build_executor()

    expense = agents[0]

    executor.execute_workflow(SUBMIT_EXPENSE_CLAIM_WORKFLOW)

    assert expense.invoke.call_count == 2


def test_employee_called_once():
    executor, agents = build_executor()

    employee = agents[1]

    executor.execute_workflow(SUBMIT_EXPENSE_CLAIM_WORKFLOW)

    employee.invoke.assert_called_once()


def test_policy_called_once():
    executor, agents = build_executor()

    policy = agents[2]

    executor.execute_workflow(SUBMIT_EXPENSE_CLAIM_WORKFLOW)

    policy.invoke.assert_called_once()
