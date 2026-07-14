"""
cli/banner.py
────────────────────────────────────────────────────────────
Professional startup banner for the Expense Management AI CLI.
"""

from __future__ import annotations

from rich.text import Text

from cli.console import console
from cli.theme import THEME

_T = THEME

APP_NAME: str = "Expense Management AI"


def show() -> None:
    """Render the startup banner to the terminal."""

    # ── Header panel ─────────────────────────────────────────────────────────
    ascii_logo = """███████╗██╗  ██╗██████╗ ███████╗███╗   ██╗███████╗
██╔════╝╚██╗██╔╝██╔══██╗██╔════╝████╗  ██║██╔════╝
█████╗   ╚███╔╝ ██████╔╝█████╗  ██╔██╗ ██║███████╗
██╔══╝   ██╔██╗ ██╔═══╝ ██╔══╝  ██║╚██╗██║╚════██║
███████╗██╔╝ ██╗██║     ███████╗██║ ╚████║███████║
╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═══╝╚══════╝"""

    header = Text(justify="center")
    header.append(ascii_logo, style=f"bold {_T.palette.brand_primary}")
    header.append("\n\n")
    header.append(f"                  {APP_NAME}\n", style=f"bold {_T.palette.text_primary}")

    console.print(header)
    console.print()

    # ── Instructions ──────────────────────────────────────────────────────────
    console.print("────────────────────────────────────────────────────────", style="dim")
    console.print("\nReady.")
    console.print("Type [bold]/help[/] to see available commands.\n")
    console.print("────────────────────────────────────────────────────────", style="dim")
    console.print()
