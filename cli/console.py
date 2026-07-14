"""
cli/console.py
────────────────────────────────────────────────────────────
Shared Rich Console singleton.

Import `console` from this module everywhere.
Never instantiate `Console()` in any other module.
"""

from __future__ import annotations

from rich.console import Console

# Single shared console — every module imports this object.
# soft_wrap is intentionally NOT set (defaults to False) so that Rich's
# word-wrap logic fires correctly inside Panels and Markdown blocks.
# safe_box=True falls back to ASCII borders on terminals that can't render
# Unicode box-drawing characters.
console: Console = Console(
    highlight=False,  # we manage highlighting ourselves via Syntax
    markup=True,
    emoji=True,
    safe_box=True,
)
