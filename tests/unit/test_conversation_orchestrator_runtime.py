from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, Mock

from agents.approval_agent import ApprovalAgent
from agents.employee_agent import EmployeeAgent
from agents.expense_agent import ExpenseAgent
from agents.policy_agent import PolicyAgent
from agents.receipt_agent import ReceiptAgent
from contracts import EmployeeProfile, PolicyContext
from conversation.conversation_state import ConversationState
from conversation.orchestrator import ConversationOrchestrator

AgentType = EmployeeAgent | ExpenseAgent | PolicyAgent | ApprovalAgent | ReceiptAgent


def _stubbed_agent(
    agent: AgentType, side_effect: Callable[..., Awaitable[object]] | Callable[..., object]
) -> AgentType:
    agent._agent.invoke_async = AsyncMock(side_effect=side_effect)
    return agent


def _build_orchestrator() -> ConversationOrchestrator:
    employee_agent = _stubbed_agent(EmployeeAgent(), _employee_side_effect)
    employee_agent.get_employee_profile = Mock(side_effect=_employee_profile_side_effect)

    policy_agent = _stubbed_agent(PolicyAgent(), _policy_side_effect)
    policy_agent.check_employee_eligibility = Mock(side_effect=_policy_eligibility_side_effect)
    policy_agent.get_category_limits = Mock(side_effect=_policy_limits_side_effect)

    expense_agent = _stubbed_agent(ExpenseAgent(), _expense_side_effect)
    approval_agent = _stubbed_agent(ApprovalAgent(), _approval_side_effect)
    receipt_agent = _stubbed_agent(ReceiptAgent(), _receipt_side_effect)

    return ConversationOrchestrator(
        employee_agent=employee_agent,
        expense_agent=expense_agent,
        policy_agent=policy_agent,
        approval_agent=approval_agent,
        receipt_agent=receipt_agent,
    )


async def _employee_side_effect(prompt: str, **kwargs: object) -> object:
    assert "EMP0006" in prompt
    return {
        "employee_id": "EMP0006",
        "employee_name": "Asha Rao",
        "employee_grade": "G5",
        "manager_id": "MGR001",
    }


async def _policy_side_effect(prompt: str, **_: object) -> dict[str, object]:
    payload = json.loads(prompt)
    task = payload["task"]
    category = payload["category_identifier"].lower()
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


async def _expense_side_effect(payload: object, **_: object) -> dict[str, object]:
    if isinstance(payload, str):
        text = payload.strip()
        try:
            structured = json.loads(text)
        except json.JSONDecodeError as err:
            if "claim status" in text.lower() or "status of claim" in text.lower():
                return {"claim_id": "CLM1001", "status": "submitted"}
            raise AssertionError(f"Unexpected expense prompt: {payload}") from err
    else:
        raise AssertionError(f"Unexpected expense prompt type: {type(payload)}")

    assert set(structured.keys()) >= {"task", "employee_profile", "policy_context", "claim"}
    claim = structured["claim"]
    assert isinstance(claim, dict)
    assert set(claim.keys()) == {
        "employee_id",
        "trip_name",
        "business_purpose",
        "destination",
        "trip_start_date",
        "trip_end_date",
        "expense_items",
    }

    policy_context = structured["policy_context"]
    assert isinstance(policy_context, dict)
    assert set(policy_context.keys()) == {"employee_grade", "categories"}
    assert policy_context["employee_grade"] == "G5"
    assert set(policy_context["categories"].keys()) == {"HOTEL", "TAXI"}

    if structured["task"] == "preview":
        return {
            "total_requested": "6700",
            "total_approved": "6500",
            "variance": "200",
            "warnings": ["Policy limits applied"],
        }
    if structured["task"] == "submit":
        return {
            "claim_id": "CLM-1001",
            "status": "submitted",
        }
    raise AssertionError(f"Unexpected expense task: {structured['task']}")


async def _approval_side_effect(prompt: str, **_: object) -> dict[str, object]:
    payload = json.loads(prompt)
    if payload["task"] == "approval":
        return {"approval_id": "APR-2001", "status": "pending"}
    raise AssertionError(f"Unexpected approval prompt: {prompt}")


async def _receipt_side_effect(prompt: str, **_: object) -> dict[str, object]:
    payload = json.loads(prompt)
    if payload["task"] == "receipt":
        return {"receipt_id": "RCT-3001", "status": "generated"}
    raise AssertionError(f"Unexpected receipt prompt: {prompt}")


def _employee_profile_side_effect(employee_id: str) -> EmployeeProfile:
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


def test_sequential_execution_generates_preview_and_waits_for_confirmation():
    orchestrator = _build_orchestrator()

    result = orchestrator.process_turn(
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )

    assert result["plan"]["pattern"] == "sequential"
    assert result["execution_result"]["stage_name"] == "PREVIEW"
    assert result["state"] == ConversationState.WAITING_USER.value
    assert "Claim Summary" in result["assistant_message"]
    assert "Do you want to submit?" in result["assistant_message"]
    assert orchestrator.employee_agent.get_employee_profile.call_count == 1
    assert orchestrator.policy_agent.check_employee_eligibility.call_count == 2
    assert orchestrator.policy_agent.get_category_limits.call_count == 2
    employee_profile = orchestrator.context.get_execution_result("employee_profile")
    assert isinstance(employee_profile, EmployeeProfile)
    assert employee_profile.employee_grade == "G5"
    assert orchestrator.expense_agent._agent.invoke_async.call_count == 1
    assert orchestrator.approval_agent._agent.invoke_async.call_count == 0
    assert orchestrator.receipt_agent._agent.invoke_async.call_count == 0

    policy_context = orchestrator.context.get_execution_result("policy_context")
    assert isinstance(policy_context, PolicyContext)
    assert policy_context.employee_grade == "G5"
    assert set(policy_context.categories.keys()) == {"HOTEL", "TAXI"}
    assert policy_context.categories["HOTEL"].eligible is True
    assert str(policy_context.categories["HOTEL"].limits["daily_limit"]) == "5000"
    assert str(policy_context.categories["TAXI"].limits["daily_limit"]) == "1500"


def test_parallel_execution_merges_policy_context_for_multiple_categories():
    orchestrator = _build_orchestrator()

    orchestrator.context.apply_updates(_claim_data())
    orchestrator.context.store_execution_result(
        "employee_profile",
        EmployeeProfile(
            employee_id="EMP0006",
            employee_name="Asha Rao",
            employee_grade="G5",
            department="Engineering",
            manager_id="MGR001",
        ),
    )

    result = orchestrator._parallel.execute(orchestrator.context)

    assert result["pattern"] == "parallel"
    assert result["stage_name"] == "POLICY"
    assert orchestrator.policy_agent.check_employee_eligibility.call_count == 2
    assert orchestrator.policy_agent.get_category_limits.call_count == 2
    employee_profile = orchestrator.context.get_execution_result("employee_profile")
    assert isinstance(employee_profile, EmployeeProfile)
    assert employee_profile.employee_grade == "G5"
    assert isinstance(result["policy_context"], PolicyContext)
    assert result["policy_context"].employee_grade == "G5"
    assert set(result["policy_context"].categories.keys()) == {"HOTEL", "TAXI"}
    assert result["policy_context"].categories["HOTEL"].eligible is True
    assert str(result["policy_context"].categories["TAXI"].limits["daily_limit"]) == "1500"


def test_human_confirmation_resume_and_finalize():
    orchestrator = _build_orchestrator()

    preview_result = orchestrator.process_turn(
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )
    assert preview_result["state"] == ConversationState.WAITING_USER.value

    submit_result = orchestrator.process_turn("YES")

    assert submit_result["plan"]["pattern"] == "sequential"
    assert orchestrator.state == ConversationState.COMPLETED
    assert orchestrator.expense_agent._agent.invoke_async.call_count == 2
    assert orchestrator.approval_agent._agent.invoke_async.call_count == 1
    assert orchestrator.receipt_agent._agent.invoke_async.call_count == 1
    assert orchestrator.context.claim_id == "CLM-1001"
    assert "Claim submitted successfully" in submit_result["assistant_message"]


def test_claim_cancellation_requires_no_persistence():
    orchestrator = _build_orchestrator()

    orchestrator.process_turn(
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )
    cancel_result = orchestrator.process_turn("NO")

    assert cancel_result["plan"]["next_action"] == "cancel"
    assert orchestrator.state == ConversationState.CANCELLED
    assert orchestrator.expense_agent._agent.invoke_async.call_count == 1
    assert orchestrator.approval_agent._agent.invoke_async.call_count == 0
    assert orchestrator.receipt_agent._agent.invoke_async.call_count == 0
    assert orchestrator.context.claim_id is None
    assert "cancelled" in cancel_result["assistant_message"].lower()


def test_end_to_end_runtime_claim_lifecycle():
    orchestrator = _build_orchestrator()

    first_turn = orchestrator.process_turn(
        "I want to submit an expense claim.",
        extracted_data=_claim_data(),
    )
    assert first_turn["state"] == ConversationState.WAITING_USER.value
    assert first_turn["execution_result"]["stage_name"] == "PREVIEW"
    assert "Do you want to submit?" in first_turn["assistant_message"]

    second_turn = orchestrator.process_turn("YES")
    assert second_turn["state"] == ConversationState.COMPLETED.value
    assert orchestrator.employee_agent.get_employee_profile.call_count == 1
    assert orchestrator.policy_agent.check_employee_eligibility.call_count == 2
    assert orchestrator.policy_agent.get_category_limits.call_count == 2
    employee_profile = orchestrator.context.get_execution_result("employee_profile")
    assert isinstance(employee_profile, EmployeeProfile)
    assert employee_profile.employee_grade == "G5"
    assert orchestrator.expense_agent._agent.invoke_async.call_count == 2
    assert orchestrator.approval_agent._agent.invoke_async.call_count == 1
    assert orchestrator.receipt_agent._agent.invoke_async.call_count == 1
    assert orchestrator.context.claim_id == "CLM-1001"
    assert orchestrator.context.confirmation is True


def test_trip_start_date_rejects_future_date_and_keeps_context():
    orchestrator = _build_orchestrator()
    orchestrator.context.apply_updates(
        {
            "employee_id": "EMP0006",
            "trip_name": "AWS Summit Bangalore 2026",
            "business_purpose": "Evaluate AWS Agentic AI for enterprise expense workflows.",
            "destination": "Bangalore",
        }
    )

    result = orchestrator.process_turn("2027-07-01")

    assert result["state"] == ConversationState.WAITING_USER.value
    assert "trip start date cannot be later than today" in result["assistant_message"].lower()
    assert orchestrator.context.trip_start_date is None
    assert orchestrator.context.execution_stage == ConversationState.WAITING_USER


def test_trip_end_date_rejects_earlier_date_and_clears_existing_value():
    orchestrator = _build_orchestrator()
    orchestrator.context.apply_updates(
        {
            "employee_id": "EMP0006",
            "trip_name": "AWS Summit Bangalore 2026",
            "business_purpose": "Evaluate AWS Agentic AI for enterprise expense workflows.",
            "destination": "Bangalore",
            "trip_start_date": "2026-07-01",
        }
    )
    orchestrator.context.expense_collection_complete = True
    orchestrator.context.set_stage(ConversationState.WAITING_USER)

    result = orchestrator.process_turn("2026-06-30")

    assert result["state"] == ConversationState.WAITING_USER.value
    assert (
        "trip end date cannot be earlier than the trip start date"
        in result["assistant_message"].lower()
    )
    assert orchestrator.context.trip_start_date == "2026-07-01"
    assert orchestrator.context.trip_end_date is None
    assert orchestrator.context.execution_stage == ConversationState.WAITING_USER
