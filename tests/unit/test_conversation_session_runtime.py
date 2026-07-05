from __future__ import annotations

import copy
import json
from typing import Any
from unittest.mock import AsyncMock, Mock

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_context import ConversationContext
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator
from conversation.session_runtime import ConversationRuntime


class FakeConversationContextRepository:
    def __init__(self) -> None:
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.deleted_sessions: list[str] = []

    def load(self, session_id: str) -> dict[str, Any] | None:
        snapshot = self.snapshots.get(session_id)
        return copy.deepcopy(snapshot) if snapshot is not None else None

    def save(self, session_id: str, snapshot: dict[str, Any]) -> None:
        self.snapshots[session_id] = copy.deepcopy(snapshot)

    def delete(self, session_id: str) -> None:
        self.deleted_sessions.append(session_id)
        self.snapshots.pop(session_id, None)


def _build_runtime(
    repository: FakeConversationContextRepository,
    loaded_contexts: list[ConversationContext],
) -> ConversationRuntime:
    employee_agent = EmployeeAgent()
    employee_agent.get_employee_profile = Mock(side_effect=_employee_profile_side_effect)

    expense_agent = ExpenseAgent()
    expense_agent.preview_claim_request = Mock(side_effect=_preview_claim_side_effect)
    expense_agent.submit_claim_request = Mock(side_effect=_submit_claim_side_effect)

    policy_agent = PolicyAgent()
    policy_agent.check_employee_eligibility = Mock(side_effect=_policy_eligibility_side_effect)
    policy_agent.get_category_limits = Mock(side_effect=_policy_limits_side_effect)

    approval_agent = ApprovalAgent()
    approval_agent.create_approval_request = Mock(side_effect=_create_approval_request_side_effect)

    receipt_agent = ReceiptAgent()
    receipt_agent.send_manager_approval_email = Mock(side_effect=_send_manager_email_side_effect)

    def _coordinator_factory(context: ConversationContext) -> CoordinatorAgent:
        loaded_contexts.append(context)
        orchestrator = ConversationOrchestrator(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
            context=context,
        )
        coordinator = CoordinatorAgent(
            employee_agent=employee_agent,
            expense_agent=expense_agent,
            policy_agent=policy_agent,
            approval_agent=approval_agent,
            receipt_agent=receipt_agent,
            conversation_orchestrator=orchestrator,
        )
        coordinator._agent.invoke_async = AsyncMock(side_effect=_classifier_side_effect)
        return coordinator

    return ConversationRuntime(
        repository=repository,
        coordinator_factory=_coordinator_factory,
    )


def _classifier_side_effect(prompt: str, **_: object) -> str:
    message = prompt.lower()
    intent = "SUBMIT_EXPENSE_CLAIM" if "submit an expense claim" in message else "UNKNOWN"
    return json.dumps({"intent": intent, "confidence": 0.99})


def _employee_profile_side_effect(employee_id: str) -> EmployeeProfile:
    return EmployeeProfile(
        employee_id=employee_id,
        employee_name="Asha Rao",
        employee_grade="G5",
        department="Engineering",
        manager_id="MGR001",
    )


def _preview_claim_side_effect(*_: object, **__: object) -> dict[str, object]:
    return {
        "total_requested": "6700",
        "total_approved": "6500",
        "variance": "200",
        "warnings": ["Policy limits applied"],
    }


def _submit_claim_side_effect(*_: object, **__: object) -> dict[str, object]:
    return {
        "claim_id": "CLM-1001",
        "status": "submitted",
    }


def _create_approval_request_side_effect(**_: object) -> dict[str, object]:
    return {
        "success": True,
        "status": "PENDING",
        "assistant_message": "Approval request created successfully.",
        "next_state": "receipt",
        "approval_result": {
            "approval_id": "APR-2001",
            "claim_id": "CLM-1001",
            "employee_id": "EMP0006",
            "approver_id": "MGR001",
            "approver_name": "Asha Rao",
            "status": "PENDING",
        },
    }


def _send_manager_email_side_effect(**_: object) -> dict[str, object]:
    return {
        "success": True,
        "status": "sent",
        "assistant_message": (
            "Claim CLM-1001 was submitted and the approval request was emailed successfully."
        ),
        "next_state": "completed",
        "receipt_result": {
            "status": "sent",
            "recipient_email": "dev@example.com",
        },
    }


def _policy_eligibility_side_effect(category_identifier: str, employee_grade: str) -> bool:
    assert employee_grade == "G5"
    assert category_identifier.upper() in {"HOTEL", "TAXI"}
    return True


def _policy_limits_side_effect(category_identifier: str, employee_grade: str) -> dict[str, object]:
    assert employee_grade == "G5"
    category = category_identifier.upper()
    if category == "HOTEL":
        return {
            "daily_limit": "5000",
            "monthly_limit": "20000",
            "receipt_required": False,
            "approval_required": False,
        }
    if category == "TAXI":
        return {
            "daily_limit": "1500",
            "monthly_limit": "10000",
            "receipt_required": False,
            "approval_required": False,
        }
    raise AssertionError(f"Unexpected policy category: {category_identifier}")


def _claim_data() -> dict[str, object]:
    return {
        "employee_id": "EMP0006",
        "trip_name": "AWS Summit Bangalore 2026",
        "business_purpose": "Evaluate AWS Agentic AI for enterprise expense workflows.",
        "destination": "Bangalore",
        "trip_start_date": "2026-07-01",
        "trip_end_date": "2026-07-03",
        "expense_items": [
            {
                "category_code": "HOTEL",
                "description": "Hotel stay",
                "expense_date": "2026-07-01",
                "requested_amount": "5800",
                "currency": "INR",
                "receipt_available": True,
            },
            {
                "category_code": "TAXI",
                "description": "Airport transfer",
                "expense_date": "2026-07-03",
                "requested_amount": "900",
                "currency": "INR",
                "receipt_available": True,
            },
        ],
    }


def test_persistent_runtime_reloads_saved_snapshot_and_resumes_conversation() -> None:
    repository = FakeConversationContextRepository()
    loaded_contexts: list[ConversationContext] = []
    runtime = _build_runtime(repository, loaded_contexts)
    session_id = "session-123"

    first_turn = runtime.process_request(
        session_id,
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )

    assert first_turn["state"] == ConversationState.WAITING_USER.value
    assert (
        repository.snapshots[session_id]["execution_stage"] == ConversationState.WAITING_USER.value
    )
    assert len(loaded_contexts) == 1
    assert isinstance(loaded_contexts[0].employee_profile, EmployeeProfile)
    assert isinstance(loaded_contexts[0].policy_context, PolicyContext)
    assert loaded_contexts[0].claim_preview is not None

    resumed_contexts: list[ConversationContext] = []
    resumed_runtime = _build_runtime(repository, resumed_contexts)
    second_turn = resumed_runtime.process_request(session_id, "YES")

    assert second_turn["state"] == ConversationState.COMPLETED.value
    assert session_id in repository.deleted_sessions
    assert session_id not in repository.snapshots
    assert len(resumed_contexts) == 1
    assert resumed_contexts[0].claim_preview is not None
    assert resumed_contexts[0].confirmation is True
    assert resumed_contexts[0].execution_stage == ConversationState.COMPLETED
