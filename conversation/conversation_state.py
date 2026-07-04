from __future__ import annotations

from enum import StrEnum


class ConversationState(StrEnum):
    """Lifecycle states for the conversational orchestrator."""

    ACTIVE = "active"
    COLLECTING_EXPENSES = "collecting_expenses"
    WAITING_USER = "waiting_user"
    EXECUTING = "executing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


__all__ = ["ConversationState"]
