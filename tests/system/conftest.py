from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import uuid4

import boto3
import pytest

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from conversation.conversation_context import ConversationContext
from conversation.orchestrator import ConversationOrchestrator


@dataclass
class LiveSystem:
    coordinator: CoordinatorAgent
    orchestrator: ConversationOrchestrator
    employee_agent: EmployeeAgent
    policy_agent: PolicyAgent
    expense_agent: ExpenseAgent
    approval_agent: ApprovalAgent
    receipt_agent: ReceiptAgent


def _has_live_credentials() -> bool:
    session = boto3.Session()
    credentials = session.get_credentials()
    return credentials is not None


def _build_claim_data(*, trip_name: str | None = None) -> dict[str, object]:
    unique_trip_name = trip_name or f"AWS Summit Bangalore {uuid4().hex[:8]}"

    return {
        "employee_id": "EMP0006",
        "trip_name": unique_trip_name,
        "business_purpose": "Evaluate AWS Agentic AI for enterprise expense workflows.",
        "destination": "Bangalore",
        "trip_start_date": date(2026, 7, 1),
        "trip_end_date": date(2026, 7, 3),
        "expense_items": [
            {
                "category_code": "HOTEL",
                "description": "Hotel stay",
                "expense_date": date(2026, 7, 1),
                "requested_amount": 5800,
                "currency": "INR",
                "receipt_available": True,
            },
            {
                "category_code": "TAXI",
                "description": "Airport transfer",
                "expense_date": date(2026, 7, 3),
                "requested_amount": 900,
                "currency": "INR",
                "receipt_available": True,
            },
        ],
    }


def _smoke_live_agents() -> None:
    temp_employee = EmployeeAgent()
    temp_policy = PolicyAgent()

    try:
        smoke_employee = temp_employee.invoke("Retrieve employee EMP0006 details.")
        smoke_policy = temp_policy.invoke("Retrieve HOTEL policy for employee grade G5.")
    except Exception as exc:  # pragma: no cover - live environment guard
        pytest.skip(f"Live system unavailable for runtime tests: {exc}")

    if smoke_employee is None or smoke_policy is None:
        pytest.skip("Live agents did not return usable smoke-test responses.")


@pytest.fixture()
def live_system() -> LiveSystem:
    if not _has_live_credentials():
        pytest.skip(
            "System tests require live AWS credentials and Bedrock access. "
            "Set up the runtime environment to exercise the real agents."
        )

    _smoke_live_agents()

    try:
        employee_agent = EmployeeAgent()
        policy_agent = PolicyAgent()
        expense_agent = ExpenseAgent()
        approval_agent = ApprovalAgent()
        receipt_agent = ReceiptAgent()
        orchestrator = ConversationOrchestrator(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
        )
        coordinator = CoordinatorAgent(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
            conversation_orchestrator=orchestrator,
        )

        return LiveSystem(
            coordinator=coordinator,
            orchestrator=orchestrator,
            employee_agent=employee_agent,
            policy_agent=policy_agent,
            expense_agent=expense_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
        )
    except Exception as exc:  # pragma: no cover - live environment guard
        pytest.skip(f"Live system unavailable for runtime tests: {exc}")


@pytest.fixture()
def claim_data() -> dict[str, object]:
    return _build_claim_data()


@pytest.fixture()
def build_claim_data():
    return _build_claim_data


@pytest.fixture()
def fresh_context() -> ConversationContext:
    return ConversationContext()
