"""
cli/session.py
────────────────────────────────────────────────────────────
SessionManager — tracks all state for a single CLI session.

Responsibilities:
  • Store the Bedrock AgentCore runtimeSessionId
  • Record conversation turns (user + assistant pairs)
  • Measure per-request latency
  • Provide session summary data for the renderer
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Final

# ─── Domain models ────────────────────────────────────────────────────────────


@dataclass
class Turn:
    """One complete request / response cycle."""

    turn_number: int
    user_message: str
    assistant_message: str
    conversation_stage: str | None
    latency_seconds: float


# ─── Session Manager ──────────────────────────────────────────────────────────

_SESSION_NOT_STARTED: Final[str] = "not-started"


class SessionManager:
    """
    Tracks all runtime state for the duration of one CLI session.

    Create one instance at application startup and thread it through
    the application via dependency injection.
    """

    def __init__(self) -> None:
        self._local_id: str = str(uuid.uuid4())[:8]
        self._runtime_session_id: str | None = None
        self._turns: list[Turn] = []
        self._start_time: float = time.monotonic()
        self._request_start: float | None = None

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def local_id(self) -> str:
        """Short local identifier shown in the footer before a runtime session exists."""
        return self._local_id

    @property
    def runtime_session_id(self) -> str | None:
        """The runtimeSessionId returned by Bedrock AgentCore."""
        return self._runtime_session_id

    @property
    def turns(self) -> list[Turn]:
        """Immutable view of all recorded turns."""
        return list(self._turns)

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def elapsed_seconds(self) -> float:
        """Wall-clock time since the session was created."""
        return time.monotonic() - self._start_time

    @property
    def last_latency(self) -> float | None:
        """Latency of the most recent turn, or None if no turns yet."""
        if self._turns:
            return self._turns[-1].latency_seconds
        return None

    @property
    def display_session_id(self) -> str:
        """Full runtime session ID for display. Never truncated."""
        if self._runtime_session_id:
            return self._runtime_session_id
        return f"local-{self._local_id}"

    # ── Mutation methods ──────────────────────────────────────────────────────

    def start_request(self) -> None:
        """Call immediately before issuing an AWS request."""
        self._request_start = time.monotonic()

    def end_request(self) -> float:
        """
        Call immediately after receiving an AWS response.
        Returns the latency in seconds.
        """
        if self._request_start is None:
            return 0.0
        latency = time.monotonic() - self._request_start
        self._request_start = None
        return latency

    def record_turn(
        self,
        *,
        user_message: str,
        assistant_message: str,
        runtime_session_id: str,
        conversation_stage: str | None,
        latency_seconds: float,
    ) -> Turn:
        """
        Persist a completed turn to session history.
        Also updates the runtime session ID from the response.
        """
        self._runtime_session_id = runtime_session_id

        turn = Turn(
            turn_number=self.turn_count + 1,
            user_message=user_message,
            assistant_message=assistant_message,
            conversation_stage=conversation_stage,
            latency_seconds=latency_seconds,
        )
        self._turns.append(turn)
        return turn

    def reset(self) -> None:
        """
        Start a new conversation thread.
        Clears the runtime session ID and all recorded turns.
        """
        self._runtime_session_id = None
        self._turns = []
        self._start_time = time.monotonic()
        self._request_start = None

    def export_history(self) -> list[dict[str, object]]:
        """Return a JSON-serialisable list of all turns."""
        return [
            {
                "turn": t.turn_number,
                "user": t.user_message,
                "assistant": t.assistant_message,
                "stage": t.conversation_stage,
                "latency_seconds": round(t.latency_seconds, 3),
            }
            for t in self._turns
        ]
