from __future__ import annotations

from agents.response_contracts import parse_agent_response
from conversation.conversation_state import ConversationState


def test_claim_submission_persists_and_can_be_queried(live_system, claim_data):
    preview = live_system.coordinator.route_message(
        "I want to submit an expense claim.",
        extracted_data=claim_data,
    )
    assert preview["state"] == ConversationState.WAITING_USER.value

    completion = live_system.coordinator.route_message("YES")
    assert completion["state"] == ConversationState.COMPLETED.value

    claim_id = live_system.orchestrator.context.claim_id
    assert claim_id

    status = live_system.coordinator.route_message(f"What is the status of claim {claim_id}?")
    status = parse_agent_response(status)
    status_text = str(status)
    if isinstance(status, dict):
        assert claim_id in str(status)
        assert "status" in str(status).lower()
    else:
        assert claim_id in status_text
        assert "status" in status_text.lower()

    approval_status = live_system.coordinator.route_message(
        f"What is the approval status of claim {claim_id}?"
    )
    approval_status = parse_agent_response(approval_status)
    approval_text = str(approval_status)
    assert claim_id in approval_text
