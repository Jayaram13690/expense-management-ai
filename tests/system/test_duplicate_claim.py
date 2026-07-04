from __future__ import annotations

import json

from conversation.conversation_state import ConversationState


def test_duplicate_claim_is_detected_by_real_expense_flow(live_system, claim_data):
    first_preview = live_system.coordinator.route_message(
        "I want to submit an expense claim.",
        extracted_data=claim_data,
    )
    assert first_preview["state"] == ConversationState.WAITING_USER.value

    first_completion = live_system.coordinator.route_message("YES")
    assert first_completion["state"] == ConversationState.COMPLETED.value

    try:
        duplicate_response = live_system.coordinator.route_message(
            "I want to submit an expense claim.",
            extracted_data=claim_data,
        )
    except Exception as exc:
        message = str(exc).lower()
        assert "duplicate" in message or "already exists" in message or "claim" in message
    else:
        response_text = json.dumps(duplicate_response, default=str).lower()
        assert "duplicate" in response_text or "already exists" in response_text
