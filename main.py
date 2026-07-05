from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from conversation.session_runtime import build_default_runtime


def print_response(response: Any) -> None:
    print("\n" + "=" * 80)
    print("\nASSISTANT:\n")
    print(_extract_assistant_text(response))
    print("=" * 80)


def _extract_assistant_text(response: Any) -> str:
    if isinstance(response, Mapping):
        message = response.get("assistant_message")
        if message is not None:
            return str(message)
        if response.get("response") is not None:
            return str(response["response"])
        return str(response)

    message = getattr(response, "message", None)
    if isinstance(message, str):
        return message
    if isinstance(message, Mapping):
        for key in ("assistant_message", "content", "text", "response"):
            value = message.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                parts = []
                for item in value:
                    if isinstance(item, Mapping):
                        text = item.get("text") or item.get("content")
                        if isinstance(text, str):
                            parts.append(text)
                    elif isinstance(item, str):
                        parts.append(item)
                if parts:
                    return "\n".join(parts)
    if hasattr(response, "text") and isinstance(response.text, str):
        return response.text
    return str(response)


def _session_id() -> str:
    session_prompt = "Session ID (leave blank for new):"
    value = os.environ.get("CONVERSATION_SESSION_ID") or input(session_prompt).strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"local-{uuid4().hex[:12]}"


def main() -> None:
    runtime = build_default_runtime()
    session_id = _session_id()

    print("\nExpense Management AI")
    print(f"Session ID: {session_id}")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("\nYou : ")
        if user_input.lower() == "exit":
            break

        response = runtime.process_request(session_id, user_input)
        print_response(response)


if __name__ == "__main__":
    main()
