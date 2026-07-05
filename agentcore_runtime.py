from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from conversation.session_runtime import build_default_runtime

_runtime = build_default_runtime()


def _extract_session_id(event: Mapping[str, Any]) -> str:
    for key in ("session_id", "conversation_id", "thread_id"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ValueError("An event session_id, conversation_id, or thread_id is required")


def _extract_message(event: Mapping[str, Any]) -> str:
    for key in ("message", "input", "text"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError("An event message, input, or text field is required")


def handle_request(event: Mapping[str, Any], _context: Any | None = None) -> dict[str, Any]:
    session_id = _extract_session_id(event)
    message = _extract_message(event)
    extracted_data = event.get("extracted_data")
    if not isinstance(extracted_data, Mapping):
        extracted_data = None
    return _runtime.process_request(session_id, message, extracted_data=extracted_data)


invoke = handle_request
main = handle_request


__all__ = ["handle_request", "invoke", "main"]


# from __future__ import annotations

# from collections.abc import Mapping
# from typing import Any

# from conversation.session_runtime import build_default_runtime

# _runtime = build_default_runtime()


# def _extract_session_id(event: Mapping[str, Any]) -> str | None:
#     """
#     Extract the conversation/session identifier if one exists.

#     AgentCore may not provide a session identifier on the very first
#     invocation, so this function returns None instead of raising.
#     """
#     for key in (
#         "runtime_session_id",
#         "session_id",
#         "conversation_id",
#         "thread_id",
#     ):
#         value = event.get(key)
#         if isinstance(value, str) and value.strip():
#             return value.strip()

#     return None


# def _extract_message(event: Mapping[str, Any]) -> str:
#     """
#     Extract the user message from the event payload.
#     """
#     for key in ("message", "input", "text"):
#         value = event.get(key)
#         if isinstance(value, str) and value.strip():
#             return value.strip()

#     raise ValueError(
#         "An event must contain one of: message, input, or text."
#     )


# def handle_request(
#     event: Mapping[str, Any],
#     _context: Any | None = None,
# ) -> dict[str, Any]:
#     """
#     AgentCore runtime entry point.
#     """

#     session_id = _extract_session_id(event)
#     message = _extract_message(event)

#     extracted_data = event.get("extracted_data")
#     if not isinstance(extracted_data, Mapping):
#         extracted_data = None

#     return _runtime.process_request(
#         session_id=session_id,
#         message=message,
#         extracted_data=extracted_data,
#     )


# # AgentCore entrypoints
# invoke = handle_request
# main = handle_request

# __all__ = [
#     "handle_request",
#     "invoke",
#     "main",
# ]
