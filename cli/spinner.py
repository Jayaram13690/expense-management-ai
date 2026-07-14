"""
cli/spinner.py
────────────────────────────────────────────────────────────
Thin wrapper around Rich Status (spinner).

Design goals:
  • Single point of control for spinner style / messaging
  • Easy to extend with execution-stage labels later
  • Used as a context manager

Usage:
    from cli.spinner import Spinner

    with Spinner("Fetching approvals…"):
        result = runtime.invoke(...)
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rich.status import Status

from cli.console import console
from cli.theme import THEME


class Spinner:
    """
    Context manager that displays a branded Rich spinner.

    Stages can be updated mid-flight to reflect execution progress:

        with Spinner() as spin:
            spin.update("Contacting runtime…")
            response = runtime.invoke(...)
            spin.update("Parsing response…")
    """

    def __init__(self, message: str | None = None) -> None:
        self._message: str = message or THEME.spinner.message
        self._status: Status | None = None

    # ── Context manager protocol ──────────────────────────────────────────────

    def __enter__(self) -> Spinner:
        self._status = console.status(
            f"[{THEME.palette.spinner_style}]{self._message}[/]",
            spinner=THEME.spinner.style,
            spinner_style=THEME.palette.spinner_style,
        )
        self._status.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._status is not None:
            self._status.__exit__(exc_type, exc_val, exc_tb)

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, message: str) -> None:
        """
        Change the spinner label mid-flight.

        This allows future callers to reflect execution stages, e.g.
            spin.update("Running tool: fetch_expenses…")
        """
        self._message = message
        if self._status is not None:
            self._status.update(f"[{THEME.palette.spinner_style}]{message}[/]")


@contextmanager
def thinking() -> Generator[Spinner]:
    """
    Convenience context manager that wraps the default 'Thinking…' spinner.

    Usage:
        with thinking():
            result = runtime.invoke(...)
    """
    with Spinner() as spin:
        yield spin
