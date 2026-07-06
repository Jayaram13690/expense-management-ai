from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from bedrock_agentcore import BedrockAgentCoreApp

from conversation.session_runtime import build_default_runtime

runtime = build_default_runtime()

app = BedrockAgentCoreApp()


def _extract_session_id(payload: Any) -> str | None:
    """
    Extract the conversation session identifier.

    On the first invocation AgentCore may not send a session id.
    ConversationRuntime should create a new conversation in that case.
    """

    if not isinstance(payload, Mapping):
        return None

    for key in (
        "sessionId",
        "runtime_session_id",
        "session_id",
        "conversation_id",
        "thread_id",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _extract_message(payload: Any) -> str:
    """
    Extract the user message from the AgentCore payload.
    """

    if isinstance(payload, str):
        return payload

    if isinstance(payload, Mapping):
        for key in (
            "message",
            "input",
            "query",
            "text",
            "prompt",
        ):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    raise ValueError("No user message found in payload.")


def _extract_extracted_data(payload: Any) -> Mapping[str, Any] | None:
    if isinstance(payload, Mapping):
        data = payload.get("extracted_data")
        if isinstance(data, Mapping):
            return data
    return None


@app.entrypoint
async def invoke(payload: Any) -> dict[str, Any]:
    """
    Amazon Bedrock AgentCore Runtime entrypoint.
    """

    # session_id = _extract_session_id(payload)
    session_id = "ac301393-df27-4104-9e46-a91da6b04d74"

    print(session_id)

    message = _extract_message(payload)

    extracted_data = _extract_extracted_data(payload)

    response = await asyncio.to_thread(
        runtime.process_request,
        session_id=session_id,
        message=message,
        extracted_data=extracted_data,
    )

    return response


if __name__ == "__main__":
    app.run()
