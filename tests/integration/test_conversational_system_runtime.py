from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, Mock

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator

AgentType = EmployeeAgent | ExpenseAgent | PolicyAgent | ApprovalAgent | ReceiptAgent


def _stub_agent(
    agent: AgentType,
    side_effect: Callable[..., Awaitable[object]] | Callable[..., object],
) -> AgentType:
    agent._agent.invoke_async = AsyncMock(side_effect=side_effect)
    return agent


def _build_system() -> CoordinatorAgent:
    _expense_side_effect.call_index = 0

    employee_agent = _stub_agent(EmployeeAgent(), _employee_side_effect)
    employee_agent.get_employee_profile = Mock(side_effect=_employee_profile_side_effect)

    expense_agent = _stub_agent(ExpenseAgent(), _expense_side_effect)
    expense_agent.get_claim_status = Mock(side_effect=_claim_status_side_effect)
    expense_agent.preview_claim_request = Mock(side_effect=_preview_claim_side_effect)
    expense_agent.submit_claim_request = Mock(side_effect=_submit_claim_side_effect)
    policy_agent = _stub_agent(PolicyAgent(), _policy_side_effect)
    policy_agent.check_employee_eligibility = Mock(side_effect=_policy_eligibility_side_effect)
    policy_agent.get_category_limits = Mock(side_effect=_policy_limits_side_effect)

    approval_agent = _stub_agent(ApprovalAgent(), _approval_side_effect)
    approval_agent.create_approval_request = Mock(side_effect=_create_approval_request_side_effect)
    receipt_agent = _stub_agent(ReceiptAgent(), _receipt_side_effect)
    receipt_agent.send_manager_approval_email = Mock(side_effect=_send_manager_email_side_effect)

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
    coordinator._agent.invoke_async = AsyncMock(side_effect=_classifier_side_effect)
    return coordinator


async def _classifier_side_effect(prompt: str, **_: object) -> str:
    message = prompt.lower()
    if "submit an expense claim" in message or "reimbursement request" in message:
        intent = "SUBMIT_EXPENSE_CLAIM"
    elif "status of claim" in message:
        intent = "CHECK_CLAIM_STATUS"
    elif "policy" in message:
        intent = "POLICY_QUERY"
    elif "employee grade" in message or "manager" in message:
        intent = "EMPLOYEE_QUERY"
    elif "approve claim" in message or "pending approvals" in message or "reject claim" in message:
        intent = "APPROVAL_QUERY"
    elif "reimbursement summary" in message or "approved receipt" in message:
        intent = "RECEIPT_QUERY"
    else:
        intent = "UNKNOWN"
    return json.dumps({"intent": intent, "confidence": 0.99})


async def _employee_side_effect(prompt: str, **_: object) -> dict[str, object]:
    if "employee profile" in prompt.lower():
        return {
            "employee_id": "EMP0006",
            "employee_name": "Asha Rao",
            "employee_grade": "G5",
            "manager_id": "MGR001",
        }
    raise AssertionError(f"Unexpected employee prompt: {prompt}")


async def _policy_side_effect(prompt: str, **_: object) -> dict[str, object]:
    lower = prompt.lower()
    if "category_identifier: hotel" in lower:
        return {
            "eligible": True,
            "daily_limit": "5000",
            "monthly_limit": "20000",
            "receipt_required": False,
            "approval_required": False,
        }
    if "category_identifier: taxi" in lower:
        return {
            "eligible": True,
            "daily_limit": "1500",
            "monthly_limit": "10000",
            "receipt_required": False,
            "approval_required": False,
        }
    raise AssertionError(f"Unexpected policy prompt: {prompt}")


async def _expense_side_effect(payload: object, **_: object) -> dict[str, object]:
    if isinstance(payload, str):
        if "claim status" in payload.lower() or "status of claim" in payload.lower():
            return {"claim_id": "CLM1001", "status": "submitted"}
        raise AssertionError(f"Unexpected expense prompt: {payload}")

    assert isinstance(payload, dict)
    assert set(payload.keys()) == {"employee_profile", "policy_context", "claim"}
    policy_context = payload["policy_context"]
    assert policy_context["employee_grade"] == "G5"
    assert set(policy_context["categories"].keys()) == {"HOTEL", "TAXI"}

    _expense_side_effect.call_index += 1
    if _expense_side_effect.call_index == 1:
        return {
            "total_requested": "6700",
            "total_approved": "6500",
            "variance": "200",
            "warnings": ["Policy limits applied"],
        }
    if _expense_side_effect.call_index == 2:
        return {"claim_id": "CLM-1001", "status": "submitted"}
    raise AssertionError("Unexpected expense invocation count")


_expense_side_effect.call_index = 0


async def _approval_side_effect(prompt: str, **_: object) -> dict[str, object]:
    if "approval request" in prompt.lower():
        return {"approval_id": "APR-2001", "status": "pending"}
    raise AssertionError(f"Unexpected approval prompt: {prompt}")


async def _receipt_side_effect(prompt: str, **_: object) -> dict[str, object]:
    if "acknowledgement" in prompt.lower():
        return {"receipt_id": "RCT-3001", "status": "generated"}
    raise AssertionError(f"Unexpected receipt prompt: {prompt}")


def _employee_profile_side_effect(employee_id: str) -> EmployeeProfile:
    return EmployeeProfile(
        employee_id=employee_id,
        employee_name="Asha Rao",
        employee_grade="G5",
        department="Engineering",
        manager_id="MGR001",
    )


def _claim_status_side_effect(claim_id: str) -> dict[str, object]:
    return {
        "success": True,
        "claim_id": claim_id,
        "status": "submitted",
        "employee_id": "EMP0006",
        "employee_name": "Asha Rao",
        "approved_amount": "6500",
        "reimbursable_amount": "6500",
    }


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


def test_end_to_end_conversational_claim_submission_uses_real_agents():
    coordinator = _build_system()

    first_turn = coordinator.route_message(
        "I want to submit an expense claim.", extracted_data=_claim_data()
    )
    assert first_turn["state"] == ConversationState.WAITING_USER.value
    assert first_turn["execution_result"]["stage_name"] == "PREVIEW"
    assert coordinator.conversation_orchestrator.employee_agent.get_employee_profile.call_count == 1
    assert (
        coordinator.conversation_orchestrator.policy_agent.check_employee_eligibility.call_count
        == 2
    )
    assert coordinator.conversation_orchestrator.policy_agent.get_category_limits.call_count == 2
    assert coordinator.conversation_orchestrator.expense_agent.preview_claim_request.call_count == 1

    policy_context = coordinator.conversation_orchestrator.context.get_execution_result(
        "policy_context"
    )
    assert isinstance(policy_context, PolicyContext)
    assert policy_context.employee_grade == "G5"
    assert set(policy_context.categories.keys()) == {"HOTEL", "TAXI"}

    second_turn = coordinator.route_message("YES")
    assert second_turn["state"] == ConversationState.COMPLETED.value
    assert coordinator.conversation_orchestrator.expense_agent.preview_claim_request.call_count == 1
    assert coordinator.conversation_orchestrator.expense_agent.submit_claim_request.call_count == 1
    assert (
        coordinator.conversation_orchestrator.approval_agent.create_approval_request.call_count == 1
    )
    assert (
        coordinator.conversation_orchestrator.receipt_agent.send_manager_approval_email.call_count
        == 1
    )
    assert coordinator.conversation_orchestrator.context.claim_id == "CLM-1001"
    assert coordinator.conversation_orchestrator.context.confirmation is True
