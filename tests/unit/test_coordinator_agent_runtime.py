from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from agents.approval_agent import ApprovalAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from contracts import EmployeeProfile
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator

AgentType = EmployeeAgent | ExpenseAgent | PolicyAgent | ApprovalAgent | ReceiptAgent


def _stub_agent(
    agent: AgentType,
    side_effect: Callable[..., Awaitable[object]] | Callable[..., object],
) -> AgentType:
    agent._agent.invoke_async = AsyncMock(side_effect=side_effect)
    return agent


def _build_coordinator() -> CoordinatorAgent:
    employee_agent = _stub_agent(EmployeeAgent(), _employee_side_effect)
    employee_agent.get_employee_profile = Mock(side_effect=_employee_profile_side_effect)

    expense_agent = _stub_agent(ExpenseAgent(), _expense_side_effect)
    policy_agent = _stub_agent(PolicyAgent(), _policy_side_effect)
    policy_agent.check_employee_eligibility = Mock(side_effect=_policy_eligibility_side_effect)
    policy_agent.get_category_limits = Mock(side_effect=_policy_limits_side_effect)

    approval_agent = _stub_agent(ApprovalAgent(), _approval_side_effect)
    receipt_agent = _stub_agent(ReceiptAgent(), _receipt_side_effect)

    orchestrator = ConversationOrchestrator(
        employee_agent=employee_agent,
        expense_agent=expense_agent,
        policy_agent=policy_agent,
        approval_agent=approval_agent,
        receipt_agent=receipt_agent,
    )
    orchestrator.process_turn = Mock(wraps=orchestrator.process_turn)

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
    if "i want to submit an expense claim" in message or "reimbursement request" in message:
        intent = "SUBMIT_EXPENSE_CLAIM"
    elif "status of claim" in message or "claim status" in message:
        intent = "CHECK_CLAIM_STATUS"
    elif "hotel policy" in message or "meal reimbursement" in message or "policy" in message:
        intent = "POLICY_QUERY"
    elif "employee grade" in message or "manager" in message:
        intent = "EMPLOYEE_QUERY"
    elif "pending approvals" in message or "approve claim" in message or "reject claim" in message:
        intent = "APPROVAL_QUERY"
    elif "reimbursement summary" in message or "approved receipt" in message:
        intent = "RECEIPT_QUERY"
    else:
        intent = "UNKNOWN"
    return json.dumps({"intent": intent, "confidence": 0.98})


async def _employee_side_effect(prompt: str, **kwargs: object) -> object:
    lower = prompt.lower()
    if "employee grade" in lower:
        return {"employee_id": "EMP0006", "employee_grade": "G5"}
    if "manager" in lower:
        return {"employee_id": "EMP0006", "manager_id": "MGR001"}
    return {"employee_id": "EMP0006"}


async def _policy_side_effect(prompt: str, **_: object) -> dict[str, object]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        category = payload["category_identifier"].lower()
        task = payload["task"]
        if category in {"hotel", "taxi"} and task in {
            "check_employee_eligibility",
            "get_category_limits",
        }:
            return {
                "eligible": True,
                "daily_limit": "5000" if category == "hotel" else "1500",
                "monthly_limit": "20000" if category == "hotel" else "10000",
                "receipt_required": True,
                "approval_required": False,
            }
        raise AssertionError(f"Unexpected policy prompt: {prompt}")

    lower = prompt.lower()
    if "hotel policy" in lower:
        return {"category": "HOTEL", "daily_limit": "5000"}
    if "meal reimbursement" in lower:
        return {"category": "MEALS", "daily_limit": "2000"}
    raise AssertionError(f"Unexpected policy prompt: {prompt}")


async def _expense_side_effect(payload: object, **_: object) -> dict[str, object]:
    if isinstance(payload, str):
        text = payload.strip()
        try:
            structured = json.loads(text)
        except json.JSONDecodeError:
            if "claim status" in text.lower() or "status of claim" in text.lower():
                return {"claim_id": "CLM1001", "status": "submitted"}
            raise AssertionError(f"Unexpected expense prompt: {payload}")

        task = structured["task"]
        if task == "preview":
            return {
                "total_requested": "6700",
                "total_approved": "6500",
                "variance": "200",
                "warnings": ["Policy limits applied"],
            }
        if task == "submit":
            return {
                "claim_id": "CLM-1001",
                "status": "submitted",
            }
        if task == "claim_status":
            return {
                "claim_id": "CLM1001",
                "status": "submitted",
            }
        raise AssertionError(f"Unexpected expense task: {task}")

    raise AssertionError(f"Unexpected expense prompt type: {type(payload)}")


async def _approval_side_effect(prompt: str, **_: object) -> dict[str, object]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        if payload["task"] == "approval":
            return {"approval_id": "APR-2001", "status": "approved"}
        raise AssertionError(f"Unexpected approval prompt: {prompt}")

    lower = prompt.lower()
    if "approve claim" in lower:
        return {"approval_id": "APR-2001", "status": "approved"}
    if "pending approvals" in lower:
        return {"queue": ["CLM1001", "CLM1002"]}
    if "reject claim" in lower:
        return {"approval_id": "APR-2002", "status": "rejected"}
    raise AssertionError(f"Unexpected approval prompt: {prompt}")


async def _receipt_side_effect(prompt: str, **_: object) -> dict[str, object]:
    try:
        payload = json.loads(prompt)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        if payload["task"] == "receipt":
            return {"receipt_id": "RCT-3001", "status": "generated"}
        raise AssertionError(f"Unexpected receipt prompt: {prompt}")

    lower = prompt.lower()
    if "reimbursement summary" in lower or "approved receipt" in lower:
        return {"receipt_id": "RCT-3001", "status": "generated"}
    raise AssertionError(f"Unexpected receipt prompt: {prompt}")


def _employee_profile_side_effect() -> EmployeeProfile:
    return EmployeeProfile(
        employee_id="EMP0006",
        employee_name="Asha Rao",
        employee_grade="G5",
        department="Engineering",
        manager_id="MGR001",
    )


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
            "receipt_required": True,
            "approval_required": False,
        }
    if category == "TAXI":
        return {
            "daily_limit": "1500",
            "monthly_limit": "10000",
            "receipt_required": True,
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


def test_submit_expense_claim_routes_through_orchestrator_and_resumes():
    coordinator = _build_coordinator()

    first = coordinator.route_message(
        "I want to submit an expense claim.", extracted_data=_claim_data()
    )
    assert first["state"] == ConversationState.WAITING_USER.value
    assert coordinator.conversation_orchestrator.process_turn.call_count == 1
    assert coordinator._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.employee_agent.get_employee_profile.call_count == 1
    assert (
        coordinator.conversation_orchestrator.policy_agent.check_employee_eligibility.call_count
        == 2
    )
    assert coordinator.conversation_orchestrator.policy_agent.get_category_limits.call_count == 2

    second = coordinator.route_message("YES")
    assert second["state"] == ConversationState.COMPLETED.value
    assert coordinator.conversation_orchestrator.process_turn.call_count == 2
    assert coordinator._agent.invoke_async.call_count == 1
    assert coordinator.expense_agent._agent.invoke_async.call_count == 2
    assert coordinator.approval_agent._agent.invoke_async.call_count == 1
    assert coordinator.receipt_agent._agent.invoke_async.call_count == 1


def test_policy_lookup_bypasses_orchestrator():
    coordinator = _build_coordinator()

    result = coordinator.route_message("What is the hotel policy?")

    assert result["category"] == "HOTEL"
    assert result["daily_limit"] == "5000"
    assert coordinator.policy_agent._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0
    assert coordinator._agent.invoke_async.call_count == 1


def test_employee_lookup_bypasses_orchestrator():
    coordinator = _build_coordinator()

    result = coordinator.route_message("What is my employee grade?")

    assert result["employee_grade"] == "G5"
    assert coordinator.employee_agent._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0


def test_approval_workflow_bypasses_orchestrator():
    coordinator = _build_coordinator()

    result = coordinator.route_message("Approve claim CLM1001")

    assert result["status"] == "approved"
    assert coordinator.approval_agent._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0


def test_receipt_generation_bypasses_orchestrator():
    coordinator = _build_coordinator()

    result = coordinator.route_message("Generate reimbursement summary")

    assert result["receipt_id"] == "RCT-3001"
    assert coordinator.receipt_agent._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0


def test_claim_status_lookup_bypasses_orchestrator():
    coordinator = _build_coordinator()

    result = coordinator.route_message("What is the status of claim CLM1001?")

    assert result["status"] == "submitted"
    assert coordinator.expense_agent._agent.invoke_async.call_count == 1
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0


def test_unknown_request_requests_clarification():
    coordinator = _build_coordinator()

    result = coordinator.route_message("Tell me something unrelated")

    assert result["intent"] == "UNKNOWN"
    assert "What would you like to do" in result["response"]
    assert coordinator.conversation_orchestrator.process_turn.call_count == 0


def test_coordinator_agent_contains_only_routing_logic():
    source = inspect.getsource(CoordinatorAgent)

    forbidden = [
        "calculate_reimbursement",
        "validate_policy_compliance",
        "detect_duplicate_claims",
        "preview_claim",
        "submit_claim",
        "get_policy_by_identifier",
        "check_employee_eligibility",
        "get_category_limits",
    ]

    for token in forbidden:
        assert token not in source
