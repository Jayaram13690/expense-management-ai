"""
cli/app.py
────────────────────────────────────────────────────────────
Application orchestrator — the main event loop.

Responsibilities:
  • Initialise all CLI sub-systems
  • Show the startup banner
  • Read user input via Prompt Toolkit
  • Dispatch slash commands
  • Invoke the AgentCore Runtime
  • Render responses and session footer
  • Update session state
  • Handle all errors gracefully

Rules:
  • No boto3 / AWS code (delegated to cli.runtime)
  • No direct print() statements (delegated to cli.renderer / cli.console)
  • No prompt_toolkit internals (delegated to cli.prompt)
"""

from __future__ import annotations

from cli import banner, commands, prompt, renderer
from cli.console import console
from cli.runtime import (
    AgentCoreRuntime,
    RuntimeClientError,
    RuntimeNetworkError,
    RuntimeParseError,
    RuntimeTimeoutError,
)
from cli.session import SessionManager
from cli.spinner import thinking
from cli.theme import THEME

_T = THEME


def run() -> None:
    """
    Entry point for the CLI application.

    Initialises all subsystems and enters the main interaction loop.
    Exits cleanly on /exit, Ctrl+D, or Ctrl+C.
    """

    # ── Initialise subsystems ─────────────────────────────────────────────────
    session = SessionManager()
    runtime = AgentCoreRuntime()

    # ── Show startup banner ───────────────────────────────────────────────────
    banner.show()

    # ── Main interaction loop ─────────────────────────────────────────────────
    while True:
        try:
            user_input = prompt.read_input()
        except KeyboardInterrupt:
            console.print(f"\n[{_T.palette.muted}]  Use [bold]/exit[/bold] or Ctrl+D to quit.[/]")
            continue
        except EOFError:
            _farewell(session)
            return

        # ── Skip empty input ──────────────────────────────────────────────────
        if not user_input:
            continue

        # ── Slash command dispatch ────────────────────────────────────────────
        if commands.is_command(user_input):
            result = commands.dispatch(user_input, session)

            if result.should_exit:
                _farewell(session)
                return

            if result.reset_session:
                session.reset()

            continue

        # ── Invoke the runtime ────────────────────────────────────────────────
        _handle_message(user_input, session, runtime)


def _handle_message(
    user_input: str,
    session: SessionManager,
    runtime: AgentCoreRuntime,
) -> None:
    """
    Send a message to the AgentCore Runtime and render the response.

    All error conditions are caught and rendered as friendly panels.
    """

    session.start_request()

    try:
        with thinking():
            response = runtime.invoke(
                user_message=user_input,
                runtime_session_id=session.runtime_session_id,
            )
    except RuntimeClientError as exc:
        latency = session.end_request()
        renderer.render_error(
            "AWS Client Error",
            "The AWS SDK returned an error.",
            str(exc),
        )
        return
    except RuntimeTimeoutError as exc:
        session.end_request()
        renderer.render_error(
            "Request Timeout",
            "The request to AgentCore Runtime timed out.",
            str(exc),
        )
        return
    except RuntimeNetworkError as exc:
        session.end_request()
        renderer.render_error(
            "Network Error",
            "Could not reach the AgentCore Runtime endpoint.",
            str(exc),
        )
        return
    except RuntimeParseError as exc:
        session.end_request()
        renderer.render_error(
            "Response Parse Error",
            "The runtime returned an unexpected response format.",
            str(exc),
        )
        return
    except Exception as exc:  # noqa: BLE001
        session.end_request()
        renderer.render_error(
            "Unexpected Error",
            "An unexpected error occurred.",
            f"{type(exc).__name__}: {exc}",
        )
        return

    latency = session.end_request()

    # ── Debug: show raw runtime response ─────────────────────────────────────
    if commands.is_debug_enabled():
        renderer.render_json(
            {
                "assistant_message": response.assistant_message,
                "conversation_stage": response.conversation_stage,
                "runtime_session_id": response.runtime_session_id,
                "latency_seconds": round(latency, 3),
            },
            title="Debug: Raw Response",
        )

    # ── Show conversation stage if present ────────────────────────────────────
    if response.conversation_stage:
        renderer.render_stage(response.conversation_stage)

    # ── Render the assistant response ─────────────────────────────────────────
    renderer.render_response(response.assistant_message)

    # ── Persist the turn to session ───────────────────────────────────────────
    session.record_turn(
        user_message=user_input,
        assistant_message=response.assistant_message,
        runtime_session_id=response.runtime_session_id,
        conversation_stage=response.conversation_stage,
        latency_seconds=latency,
    )

    # ── Render the session footer ─────────────────────────────────────────────
    renderer.render_session_footer(session)


def _farewell(session: SessionManager) -> None:
    """Render a goodbye message and exit cleanly."""
    console.print(
        f"\n[{_T.palette.brand_primary}]{_T.icons.sparkle}  Goodbye! "
        f"Session had {session.turn_count} turn(s).[/]\n"
    )
