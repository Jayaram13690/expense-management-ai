"""
cli/prompt.py
────────────────────────────────────────────────────────────
Interactive prompt powered by Prompt Toolkit.

Features:
  • Named command history (persisted to ~/.expense_ai_history)
  • Multiline input (Meta+Enter or Esc+Enter)
  • Slash command completion + auto-suggestions
  • Ctrl+C  → raise KeyboardInterrupt (caller handles gracefully)
  • Ctrl+D  → raise EOFError (caller handles gracefully)
  • Modern coloured prompt:   ExpenseAI ❯
"""

from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from cli.theme import THEME

_T = THEME

# ── History file ──────────────────────────────────────────────────────────────

_HISTORY_FILE: Path = Path.home() / ".expense_ai_history"

# ── Slash commands available for completion ───────────────────────────────────

SLASH_COMMANDS: list[str] = [
    "/help",
    "/new",
    "/cancel",
    "/clear",
    "/session",
    "/history",
    "/export",
    "/debug",
    "/exit",
]

# ── Prompt Toolkit style ──────────────────────────────────────────────────────

_PROMPT_STYLE: Style = Style.from_dict(
    {
        "label": "#00d7d7 bold",  # ExpenseAI
        "chevron": "#00d7d7 bold",  # ❯
        "bottom-toolbar": "bg:#1c1c1c #888888",
    }
)


# ── Slash command completer ───────────────────────────────────────────────────


class SlashCommandCompleter(Completer):
    """Complete slash commands when the input starts with '/'."""

    def get_completions(self, document: object, complete_event: object):  # type: ignore[override]
        from prompt_toolkit.document import Document  # local import to avoid circular

        assert isinstance(document, Document)
        text = document.text_before_cursor

        if not text.startswith("/"):
            return

        for cmd in SLASH_COMMANDS:
            if cmd.startswith(text):
                yield Completion(
                    cmd[len(text) :],
                    start_position=0,
                    display=cmd,
                )


# ── Session factory ───────────────────────────────────────────────────────────


def _build_prompt_session() -> PromptSession[str]:
    """Build and return a configured PromptSession."""
    history = FileHistory(str(_HISTORY_FILE))

    bindings = KeyBindings()

    # Allow Ctrl+J (newline) for multiline within a single input —
    # Prompt Toolkit uses Ctrl+J as Enter by default; Meta+Enter inserts a
    # literal newline so users can type multiline messages.
    @bindings.add("escape", "enter")
    def _insert_newline(event: object) -> None:  # type: ignore[type-arg]
        from prompt_toolkit.buffer import Buffer  # local import

        assert hasattr(event, "app")
        buf: Buffer = event.app.current_buffer
        buf.insert_text("\n")

    return PromptSession(
        history=history,
        auto_suggest=AutoSuggestFromHistory(),
        completer=SlashCommandCompleter(),
        complete_while_typing=True,
        style=_PROMPT_STYLE,
        key_bindings=bindings,
        multiline=False,  # single Enter submits; Esc+Enter inserts newline
        enable_history_search=True,
    )


# ── Public interface ──────────────────────────────────────────────────────────

# Lazily-initialised PromptSession — created on first call to read_input().
# This defers the Win32 console detection until the terminal is actually open,
# which avoids NoConsoleScreenBufferError when the module is imported in a
# non-interactive context (e.g. unit tests, import-time checks).
_session: PromptSession[str] | None = None


def _get_session() -> PromptSession[str]:
    """Return the shared PromptSession, creating it on first call."""
    global _session
    if _session is None:
        _session = _build_prompt_session()
    return _session


def read_input() -> str:
    """
    Display the prompt and block until the user presses Enter.

    Returns
    -------
    str
        The stripped user input.

    Raises
    ------
    KeyboardInterrupt
        When the user presses Ctrl+C.
    EOFError
        When the user presses Ctrl+D or the input stream is closed.
    """
    prompt_tokens: list[tuple[str, str]] = [
        ("class:label", "ExpenseAI "),
        ("class:chevron", f"{_T.icons.chevron} "),
    ]

    raw: str = _get_session().prompt(prompt_tokens)  # type: ignore[arg-type]
    return raw.strip()
