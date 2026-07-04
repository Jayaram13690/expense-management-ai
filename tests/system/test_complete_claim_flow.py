from __future__ import annotations

from contracts import PolicyContext
from conversation.conversation_state import ConversationState


def _normalize(value):
    if hasattr(value, "model_dump") and callable(value.model_dump):
        return value.model_dump()
    return value


def test_complete_claim_flow(live_system, claim_data):
    first_turn = live_system.coordinator.route_message(
        "I want to submit an expense claim.",
        extracted_data=claim_data,
    )

    assert first_turn["state"] == ConversationState.WAITING_USER.value
    assert "Claim Summary" in first_turn["assistant_message"]
    assert "Do you want to submit?" in first_turn["assistant_message"]
    assert first_turn["execution_result"]["stage_name"] == "PREVIEW"

    policy_context = live_system.orchestrator.context.get_execution_result("policy_context")
    assert isinstance(policy_context, PolicyContext)
    assert policy_context.employee_grade == "G5"
    assert set(policy_context.categories.keys()) == {"HOTEL", "TAXI"}

    second_turn = live_system.coordinator.route_message("YES")

    assert second_turn["state"] == ConversationState.COMPLETED.value
    assert "Claim submitted successfully" in second_turn["assistant_message"]
    assert live_system.orchestrator.context.confirmation is True
    assert live_system.orchestrator.context.claim_id
    assert live_system.orchestrator.context.get_execution_result("approval_result") is not None
    assert live_system.orchestrator.context.get_execution_result("receipt_result") is not None

    submitted = live_system.orchestrator.context.get_execution_result("submitted_claim")
    assert submitted is not None
    submitted = _normalize(submitted)
    if isinstance(submitted, dict):
        assert submitted.get("claim_id") == live_system.orchestrator.context.claim_id
