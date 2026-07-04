from __future__ import annotations

from conversation.conversation_state import ConversationState


def test_conversation_resume_after_missing_information(live_system, claim_data):
    first_turn = live_system.coordinator.route_message("I want to submit an expense claim.")

    assert first_turn["state"] == ConversationState.WAITING_USER.value
    assert first_turn["assistant_message"]

    second_turn = live_system.coordinator.route_message(
        "Here are the trip details you asked for.",
        extracted_data=claim_data,
    )

    assert second_turn["state"] == ConversationState.WAITING_USER.value
    assert "Claim Summary" in second_turn["assistant_message"]
    assert live_system.orchestrator.state == ConversationState.WAITING_USER

    final_turn = live_system.coordinator.route_message("YES")

    assert final_turn["state"] == ConversationState.COMPLETED.value
    assert live_system.orchestrator.state == ConversationState.COMPLETED
    assert live_system.orchestrator.context.confirmation is True
    assert live_system.orchestrator.context.claim_id is not None
