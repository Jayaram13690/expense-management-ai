"""
cli/commands.py
────────────────────────────────────────────────────────────
Slash command registry and implementations.

Architecture:
  • Each command is a standalone function with a consistent signature.
  • Commands are registered in the REGISTRY dict keyed by their slash token.
  • The dispatcher `dispatch()` looks up and calls the handler.
  • Adding a new command requires only: write a handler + add one registry entry.

Supported commands:
  /help     – Print command reference
  /new      – Reset the conversation session
  /cancel   – Explicitly cancel the active workflow and clear session
  /clear    – Clear the terminal screen
  /session  – Display current session details
  /history  – Render conversation history
  /export   – Export history to a timestamped JSON file
  /debug    – Toggle debug mode (prints raw runtime responses)
  /exit     – Terminate the application
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from cli.console import console
from cli.renderer import (
    print_blank,
    render_history,
    render_info,
    render_json,
    render_success,
    render_warning,
)
from cli.theme import THEME

if TYPE_CHECKING:
    from cli.session import SessionManager

_T = THEME

# ── Command result ─────────────────────────────────────────────────────────────


@dataclass
class CommandResult:
    """
    Returned by every command handler so the application loop can
    decide what to do next.
    """

    handled: bool = True
    should_exit: bool = False
    reset_session: bool = False


# ── Type alias for a command handler ─────────────────────────────────────────

CommandHandler = Callable[["SessionManager", list[str]], CommandResult]


# ── Global state ─────────────────────────────────────────────────────────────

_debug_enabled: bool = False


def is_debug_enabled() -> bool:
    """Return True if debug mode is active."""
    return _debug_enabled


# ── Handlers ─────────────────────────────────────────────────────────────────


def _cmd_help(session: SessionManager, args: list[str]) -> CommandResult:
    """Display the command reference table."""
    from rich import box
    from rich.table import Table

    table = Table(
        title=f"[bold {_T.palette.brand_primary}]{_T.icons.sparkle} Available Commands[/]",
        box=box.ROUNDED,
        border_style=_T.palette.border,
        header_style=f"bold {_T.palette.brand_primary}",
        show_lines=False,
        padding=(0, 1),
    )

    table.add_column("Command", style=f"bold {_T.palette.brand_primary}", width=14)
    table.add_column("Description", style=_T.palette.muted)

    commands_info = [
        ("/help", "Show help"),
        ("/new", "Start new conversation"),
        ("/cancel", "Cancel current workflow"),
        ("/session", "Session information"),
        ("/history", "Conversation history"),
        ("/export", "Export history"),
        ("/debug", "Toggle debug mode"),
        ("/clear", "Clear terminal"),
        ("/exit", "Exit CLI"),
    ]

    for cmd, desc in commands_info:
        table.add_row(cmd, desc)

    console.print()
    console.print(table)
    print_blank()

    return CommandResult(handled=True)


def _cmd_new(session: SessionManager, args: list[str]) -> CommandResult:
    """Reset the session so a new conversation thread starts."""
    render_warning("Starting a new session. The previous conversation context has been cleared.")
    return CommandResult(handled=True, reset_session=True)


def _cmd_cancel(session: SessionManager, args: list[str]) -> CommandResult:
    """
    Cancel the active workflow, delete the conversation snapshot, and clear the CLI session.
    """
    if session.runtime_session_id is None:
        render_warning("No active workflow to cancel.")
        return CommandResult(handled=True)

    # 1. Delete the conversation snapshot from DynamoDB using the existing repository
    # Temporarily suppress backend logging (like AWS initialization) to keep the CLI clean
    import logging

    logging.disable(logging.CRITICAL)
    try:
        from conversation.context_repository import ConversationContextRepository

        repository = ConversationContextRepository()

        # Use the fixed session ID that agentcore_runtime.py is using for local development
        session_id = "ac301393-df27-4104-9e46-a91da6b04d74"
        repository.delete(session_id)
    finally:
        logging.disable(logging.NOTSET)

    render_warning(
        "Workflow cancelled. "
        "The active expense claim session has been abandoned.\n"
        "Start a new message to begin a fresh conversation."
    )
    return CommandResult(handled=True, reset_session=True)


def _cmd_clear(session: SessionManager, args: list[str]) -> CommandResult:
    """Clear the terminal screen."""
    os.system("cls" if sys.platform == "win32" else "clear")
    return CommandResult(handled=True)


def _cmd_session(session: SessionManager, args: list[str]) -> CommandResult:
    """Display current session metadata."""

    elapsed = session.elapsed_seconds
    minutes, seconds = divmod(int(elapsed), 60)
    elapsed_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    data = {
        "session_id": session.display_session_id,
        "runtime_session_id": session.runtime_session_id or "Not started",
        "turn_count": session.turn_count,
        "elapsed": elapsed_str,
        "last_latency": (
            f"{session.last_latency:.2f}s" if session.last_latency is not None else "N/A"
        ),
    }

    render_json(data, title=f"{_T.icons.session} Session Info")
    return CommandResult(handled=True)


def _cmd_history(session: SessionManager, args: list[str]) -> CommandResult:
    """Render the full conversation history."""
    render_history(session)
    return CommandResult(handled=True)


def _cmd_export(session: SessionManager, args: list[str]) -> CommandResult:
    """
    Export conversation history to a JSON file.

    The filename is auto-generated with a timestamp, e.g.:
        expense_ai_history_20261214_152300.json
    """
    turns = session.export_history()

    if not turns:
        render_warning("No conversation history to export.")
        return CommandResult(handled=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"expense_ai_history_{timestamp}.json"

    try:
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "session_id": session.display_session_id,
                    "exported_at": datetime.now().isoformat(),
                    "turns": turns,
                },
                fh,
                indent=2,
            )
        render_success(f"History exported to: {filename}")
    except OSError as exc:
        from cli.renderer import render_error

        render_error("Export Failed", "Could not write the export file.", str(exc))

    return CommandResult(handled=True)


def _cmd_debug(session: SessionManager, args: list[str]) -> CommandResult:
    """Toggle debug mode."""
    global _debug_enabled
    _debug_enabled = not _debug_enabled

    if _debug_enabled:
        render_info("Debug Mode", "Debug mode ENABLED. Raw runtime responses will be logged.")
    else:
        render_info("Debug Mode", "Debug mode DISABLED.")

    return CommandResult(handled=True)


def _cmd_exit(session: SessionManager, args: list[str]) -> CommandResult:
    """Signal the application to exit."""
    return CommandResult(handled=True, should_exit=True)


# ── Command registry ──────────────────────────────────────────────────────────

REGISTRY: dict[str, CommandHandler] = {
    "/help": _cmd_help,
    "/new": _cmd_new,
    "/cancel": _cmd_cancel,
    "/clear": _cmd_clear,
    "/session": _cmd_session,
    "/history": _cmd_history,
    "/export": _cmd_export,
    "/debug": _cmd_debug,
    "/exit": _cmd_exit,
    # Aliases
    "/quit": _cmd_exit,
    "exit": _cmd_exit,
    "quit": _cmd_exit,
}


# ── Public dispatcher ─────────────────────────────────────────────────────────


def is_command(text: str) -> bool:
    """Return True if the text matches a registered command."""
    token = text.strip().split()[0].lower() if text.strip() else ""
    return token in REGISTRY


def dispatch(text: str, session: SessionManager) -> CommandResult:
    """
    Look up and execute the matching command handler.

    Parameters
    ----------
    text:
        The raw user input (e.g. "/export myfile").
    session:
        The active SessionManager, passed to every handler.

    Returns
    -------
    CommandResult
        Indicates whether to exit, reset the session, etc.
        Returns ``CommandResult(handled=False)`` when no handler matches.
    """
    parts = text.strip().split()
    if not parts:
        return CommandResult(handled=False)

    token = parts[0].lower()
    args = parts[1:]

    handler = REGISTRY.get(token)

    if handler is None:
        render_warning(
            f"Unknown command: [bold]{token}[/]. Type [bold]/help[/] for available commands."
        )
        return CommandResult(handled=True)

    return handler(session, args)
