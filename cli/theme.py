"""
cli/theme.py
────────────────────────────────────────────────────────────
Centralised design tokens for the Expense Management AI CLI.

Every colour, icon, border style, and text style lives here.
No other module should hard-code colour names or panel styles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── Colour palette ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Palette:
    """
    HSL-tuned colour tokens.  All values are Rich markup colour strings.
    """

    # Brand
    brand_primary: str = "bright_cyan"
    brand_secondary: str = "cyan"
    brand_accent: str = "bright_blue"

    # Semantic
    success: str = "bright_green"
    warning: str = "yellow"
    error: str = "bright_red"
    muted: str = "grey62"
    dim: str = "grey37"

    # Text
    text_primary: str = "bright_white"
    text_secondary: str = "white"
    text_code: str = "bright_yellow"

    # UI chrome
    border: str = "cyan"
    border_dim: str = "grey37"
    header_bg: str = "dark_cyan"
    footer_text: str = "grey62"

    # Prompt
    prompt_chevron: str = "bright_cyan"
    prompt_label: str = "bright_white"

    # Spinner
    spinner_style: str = "bright_cyan"


# ─── Icon / glyph tokens ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Icons:
    # Status
    success: str = "✓"
    warning: str = "⚠"
    error: str = "✗"
    info: str = "i"

    # Navigation
    chevron: str = "❯"
    bullet: str = "•"
    arrow: str = "→"

    # Sections
    assistant: str = "🤖"
    user: str = "👤"
    session: str = "🔗"
    clock: str = "⏱"
    sparkle: str = "✨"
    rocket: str = "🚀"
    brain: str = "🧠"


# ─── Panel / border styles ────────────────────────────────────────────────────


@dataclass(frozen=True)
class PanelStyles:
    """Rich border style names for panels."""

    banner: str = "double"
    response: str = "rounded"
    error: str = "heavy"
    warning: str = "rounded"
    success: str = "rounded"
    info: str = "rounded"
    session: str = "minimal"
    command: str = "simple"


# ─── Text styles ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TextStyles:
    """Rich markup style strings for common text roles."""

    heading: str = "bold bright_white"
    subheading: str = "bold cyan"
    label: str = "bold bright_cyan"
    value: str = "bright_white"
    muted: str = "grey62"
    code: str = "bold bright_yellow"
    link: str = "underline bright_cyan"
    stage: str = "italic grey62"


# ─── Spinner config ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SpinnerConfig:
    style: str = "dots"
    message: str = "Thinking…"
    speed: float = 1.0


# ─── Assembled theme ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Theme:
    palette: Palette = field(default_factory=Palette)
    icons: Icons = field(default_factory=Icons)
    panels: PanelStyles = field(default_factory=PanelStyles)
    text: TextStyles = field(default_factory=TextStyles)
    spinner: SpinnerConfig = field(default_factory=SpinnerConfig)


# Module-level singleton — import this everywhere
THEME: Theme = Theme()
