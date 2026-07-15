"""
cli/runtime.py
────────────────────────────────────────────────────────────
All AWS Bedrock AgentCore Runtime interactions live here.

Responsibilities:
  • Create and own the boto3 bedrock-agentcore client
  • Invoke the AgentCore Runtime endpoint
  • Parse the raw response body into a strongly-typed object
  • Raise meaningful, domain-specific exceptions

Rules:
  • No Rich / console code
  • No print statements
  • No business logic
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError, EndpointResolutionError
from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file) so the CLI
# picks up environment variables when run locally without any shell export.
load_dotenv()

# ─── Configuration (loaded from .env / environment) ──────────────────────────

REGION: str = os.getenv("AGENTCORE_REGION", "us-east-1")

RUNTIME_ARN: str = os.getenv("AGENTCORE_RUNTIME_ARN", "")

if not RUNTIME_ARN:
    raise OSError(
        "AGENTCORE_RUNTIME_ARN is not set.\n"
        "Add it to your .env file:\n"
        "  AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:<3region>:<account>:runtime/<name>"
    )


# ─── Typed response ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuntimeResponse:
    """Strongly typed representation of a successful AgentCore response."""

    assistant_message: str
    conversation_stage: str | None
    runtime_session_id: str


# ─── Exceptions ───────────────────────────────────────────────────────────────


class RuntimeError(Exception):  # noqa: A001
    """Base class for all AgentCore Runtime errors."""


class RuntimeClientError(RuntimeError):
    """Raised when the AWS boto3 client returns a ClientError."""

    def __init__(self, cause: ClientError) -> None:
        error_code = cause.response.get("Error", {}).get("Code", "Unknown")
        error_msg = cause.response.get("Error", {}).get("Message", str(cause))
        super().__init__(f"[{error_code}] {error_msg}")
        self.cause = cause


class RuntimeParseError(RuntimeError):
    """Raised when the response body cannot be parsed."""

    def __init__(self, body: str, reason: str) -> None:
        super().__init__(f"Failed to parse runtime response — {reason}\nRaw body: {body!r}")
        self.body = body


class RuntimeTimeoutError(RuntimeError):
    """Raised on a read timeout or connect timeout."""


class RuntimeNetworkError(RuntimeError):
    """Raised on network-level failures (no connectivity, DNS, etc.)."""


# ─── Client factory ───────────────────────────────────────────────────────────


def _make_client() -> Any:
    """
    Create the boto3 bedrock-agentcore client.

    Wrapped in a function so callers can inject a mock for testing.
    """
    return boto3.client(
        "bedrock-agentcore",
        region_name=REGION,
    )


# ─── AgentCore invocation ─────────────────────────────────────────────────────


class AgentCoreRuntime:
    """
    Encapsulates all AWS calls for the Bedrock AgentCore Runtime.

    Usage:
        runtime = AgentCoreRuntime()
        response = runtime.invoke(user_message="...", runtime_session_id="...")
    """

    def __init__(self, client: Any | None = None) -> None:
        self._client: Any = client if client is not None else _make_client()

    def invoke(
        self,
        *,
        user_message: str,
        runtime_session_id: str | None = None,
    ) -> RuntimeResponse:
        """
        Invoke the AgentCore Runtime and return a typed response.

        Parameters
        ----------
        user_message:
            The plain-text message from the user.
        runtime_session_id:
            The session ID from a previous response, or None for a new session.

        Returns
        -------
        RuntimeResponse
            Parsed, strongly-typed response from the runtime.

        Raises
        ------
        RuntimeClientError:
            When AWS returns a ClientError (e.g. auth, throttling, not-found).
        RuntimeParseError:
            When the response body is malformed.
        RuntimeTimeoutError:
            When the request times out.
        RuntimeNetworkError:
            When the network is unreachable.
        """

        request_payload: dict[str, str] = {"message": user_message}

        kwargs: dict[str, Any] = {
            "agentRuntimeArn": RUNTIME_ARN,
            "contentType": "application/json",
            "accept": "application/json",
            "payload": json.dumps(request_payload).encode(),
        }

        if runtime_session_id:
            kwargs["runtimeSessionId"] = runtime_session_id

        try:
            raw_response: dict[str, Any] = self._client.invoke_agent_runtime(**kwargs)
        except ClientError as exc:
            raise RuntimeClientError(exc) from exc
        except EndpointResolutionError as exc:
            raise RuntimeNetworkError(f"Cannot resolve the AWS endpoint: {exc}") from exc
        except Exception as exc:
            # Catch botocore read-timeout and connect-timeout
            exc_name = type(exc).__name__
            if "Timeout" in exc_name or "timeout" in str(exc).lower():
                raise RuntimeTimeoutError(f"Request to AgentCore Runtime timed out: {exc}") from exc
            raise RuntimeNetworkError(
                f"Network error while contacting AgentCore Runtime: {exc}"
            ) from exc

        # ── Extract runtime session ID ────────────────────────────────────────
        new_runtime_session_id: str = raw_response.get("runtimeSessionId", runtime_session_id or "")

        # ── Read and decode the streaming body ───────────────────────────────
        body: str = _read_body(raw_response)

        # ── Parse the JSON body ───────────────────────────────────────────────
        return _parse_body(body, new_runtime_session_id)


# ─── Private helpers ──────────────────────────────────────────────────────────


def _read_body(raw_response: dict[str, Any]) -> str:
    """
    Read and decode the response body from the AgentCore streaming object.
    """
    try:
        response_obj = raw_response["response"]
        return response_obj.read().decode("utf-8")
    except (KeyError, AttributeError, UnicodeDecodeError) as exc:
        raise RuntimeParseError("", f"Cannot read response body: {exc}") from exc


def _parse_body(body: str, runtime_session_id: str) -> RuntimeResponse:
    """
    Parse the raw JSON body and return a RuntimeResponse.

    The AgentCore Runtime currently returns:
        {
            "assistant_message": "...",
            "conversation_stage": "...",   # optional
            "session_id": "..."            # optional
        }

    Fallback: if the body is not valid JSON, treat the raw string as the message.
    """
    try:
        result: Any = json.loads(body)
    except json.JSONDecodeError:
        # Non-JSON body — treat entire payload as the message.
        if body.strip():
            return RuntimeResponse(
                assistant_message=body.strip(),
                conversation_stage=None,
                runtime_session_id=runtime_session_id,
            )
        raise RuntimeParseError(body, "Body is not valid JSON and is empty.") from None

    if isinstance(result, dict):
        assistant_message: str = result.get("assistant_message") or "No response received."
        conversation_stage: str | None = result.get("conversation_stage") or None
        return RuntimeResponse(
            assistant_message=assistant_message,
            conversation_stage=conversation_stage,
            runtime_session_id=runtime_session_id,
        )

    if isinstance(result, str):
        return RuntimeResponse(
            assistant_message=result or "No response received.",
            conversation_stage=None,
            runtime_session_id=runtime_session_id,
        )

    raise RuntimeParseError(body, f"Unexpected response type: {type(result).__name__}")
