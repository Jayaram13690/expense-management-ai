"""
cli/__init__.py
────────────────────────────────────────────────────────────
Public re-exports for the cli package.

Only the symbols that external callers (chat.py) need are exposed here.
"""

from __future__ import annotations

from cli.app import run

__all__: list[str] = ["run"]
