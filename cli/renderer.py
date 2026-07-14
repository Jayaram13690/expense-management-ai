"""
cli/renderer.py
────────────────────────────────────────────────────────────
All terminal rendering lives here.

Responsibilities:
  • Render Markdown (with syntax-highlighted code blocks)
  • Render JSON with syntax highlighting
  • Render Rich tables
  • Render panels (response, error, warning, success, info)
  • Render the session footer after each turn
  • Render conversation stage hints

Rules:
  • No business logic
  • No AWS / boto3 code
  • No input() / prompt_toolkit interactions
"""

from __future__ import annotations

import json as _json
import re
from dataclasses import dataclass, field
from typing import Any

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from cli.console import console
from cli.session import SessionManager
from cli.theme import THEME

_T = THEME  # shorthand


# ─── Internal helpers ─────────────────────────────────────────────────────────


def _rule(title: str = "", style: str = "") -> None:
    """Print a styled horizontal rule."""
    console.print(Rule(title=title, style=style or _T.palette.border_dim))


# ─── Claim Summary detection & rendering ─────────────────────────────────────

_CLAIM_SUMMARY_RE: re.Pattern[str] = re.compile(r"claim\s+summary", re.IGNORECASE)

# Matches any of the three total fields — with or without Markdown bold markers,
# colons, currency symbols, or extra whitespace.
_TOTAL_RE: re.Pattern[str] = re.compile(
    r"\*{0,2}(claimed\s+amount|approved\s+amount|variance)\*{0,2}[:\s]+([\d,\.$₹£€]+)",
    re.IGNORECASE,
)

# Lines that are pure structural noise and must be dropped from the remainder.
_SKIP_LINE_RE: re.Pattern[str] = re.compile(
    r"^\*{0,2}claim\s+summary\*{0,2}\s*$"
    r"|^\*{0,2}(claimed\s+amount|approved\s+amount|variance)\*{0,2}[:\s]+[\d,\.$₹£€]+\s*$",
    re.IGNORECASE,
)

# Inline section patterns — the runtime emits everything on one line.
_WARN_INLINE_RE: re.Pattern[str] = re.compile(
    r"warnings?\s*:\s*(.+?)(?=applied\s+policy\s+limits?\s*:|do\s+you\s+want|"
    r"would\s+you\s+like\s+to\s+submit|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_POLICY_INLINE_RE: re.Pattern[str] = re.compile(
    r"applied\s+policy\s+limits?\s*:\s*(.+?)(?=do\s+you\s+want|"
    r"would\s+you\s+like\s+to\s+submit|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_SUBMIT_INLINE_RE: re.Pattern[str] = re.compile(
    r"(do\s+you\s+want\s+to\s+submit[^?]*\??|"
    r"would\s+you\s+like\s+to\s+submit[^?]*\??|"
    r"submit\s+this\s+claim\??)",
    re.IGNORECASE,
)


@dataclass
class _PolicyLimit:
    category: str
    limits: list[tuple[str, str]] = field(default_factory=list)


def _is_claim_summary(text: str) -> bool:
    """Return True when the response looks like a Claim Summary report."""
    return bool(_CLAIM_SUMMARY_RE.search(text))


def _extract_totals(text: str) -> tuple[str, str, str]:
    """
    Scan the whole message for claimed/approved/variance values.
    Extracts only the FIRST occurrence of each to avoid capturing
    individual expense line item totals that appear later in the text.
    Returns (claimed, approved, variance) — each may be an empty string.
    """
    claimed = approved = variance = ""
    for m in _TOTAL_RE.finditer(text):
        key = m.group(1).lower().replace(" ", "_")
        val = m.group(2).strip()
        if "claimed" in key and not claimed:
            claimed = val
        elif "approved" in key and not approved:
            approved = val
        elif "variance" in key and not variance:
            variance = val

        # Optimization: break early if we found all three
        if claimed and approved and variance:
            break

    return claimed, approved, variance


def _extract_remainder(text: str) -> str:
    """
    Return the portion of the message that is NOT the title line and NOT
    a totals line — i.e. warnings, policy limits, submit prompt, etc.
    """
    kept: list[str] = []
    for line in text.splitlines():
        if not _SKIP_LINE_RE.match(line.strip()):
            kept.append(line)

    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()

    return "\n".join(kept)


def _parse_inline_sections(
    remainder: str,
) -> tuple[list[str], list[_PolicyLimit], str]:
    """
    Parse the inline-format remainder the runtime actually produces:

      Warnings: Cat: text.; Cat: text. Applied Policy Limits: CAT: k=v, k=v

      Do you want to submit?

    Returns:
      warning_items  – flat list of warning strings (one per bullet)
      policy_limits  – list of _PolicyLimit with key/value rows
      submit_text    – the submit/confirmation prompt string
    """
    # Collapse to a single line so all regexes work across soft-wrapped output.
    flat = " ".join(remainder.split())

    warning_items: list[str] = []
    policy_limits: list[_PolicyLimit] = []
    submit_text: str = ""

    # ── Submit prompt ─────────────────────────────────────────────────────────
    sm = _SUBMIT_INLINE_RE.search(flat)
    if sm:
        submit_text = sm.group(0).strip()

    # ── Warnings ──────────────────────────────────────────────────────────────
    wm = _WARN_INLINE_RE.search(flat)
    if wm:
        raw = wm.group(1).strip().rstrip(".")
        for item in re.split(r";\s*", raw):
            item = item.strip().rstrip(".").strip()
            if item:
                warning_items.append(item)

    # ── Policy limits ─────────────────────────────────────────────────────────
    pm = _POLICY_INLINE_RE.search(flat)
    if pm:
        pol_text = pm.group(1).strip()
        # Remove any submit prompt that leaked into the match
        if sm:
            cut = pol_text.lower().find(sm.group(0).lower())
            if cut != -1:
                pol_text = pol_text[:cut].strip()

        # Each category block starts with an ALL-CAPS word followed by a colon,
        # e.g. "HOTEL: k=v, k=v  MEALS: k=v, k=v".
        # Split on whitespace that precedes an all-caps token ending in ":".
        blocks = re.split(r"(?<=\S)\s+(?=[A-Z][A-Z_]*:)", pol_text)
        for block in blocks:
            block = block.strip()
            cat_m = re.match(r"([A-Z][A-Z_]*):\s*(.+)", block, re.IGNORECASE)
            if not cat_m:
                continue
            cat = cat_m.group(1).upper()
            kvs_str = cat_m.group(2).strip().rstrip(".,")
            pl = _PolicyLimit(category=cat)
            for kv in re.split(r",\s*", kvs_str):
                kv = kv.strip()
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    # Pretty-print: daily_limit → Daily Limit, True → Required
                    pretty_k = k.strip().replace("_", " ").title()
                    raw_v = v.strip()
                    pretty_v = (
                        "Required"
                        if raw_v.lower() == "true"
                        else "Not Required" if raw_v.lower() == "false" else raw_v
                    )
                    pl.limits.append((pretty_k, pretty_v))
            if pl.limits or cat:
                policy_limits.append(pl)

    return warning_items, policy_limits, submit_text


def render_claim_summary(message: str) -> None:
    """
    Render a Claim Summary using Rich Panel, Tables, Rules, and bullet lists.

    Architecture:
      1. Structured totals table — always rendered (format-agnostic regex scan).
      2. Inline-format parser — splits the semicolon-separated warnings and
         key=value policy limits into Rich bullet lists and tables.
      3. Markdown fallback — only used when the inline parser finds nothing,
         so nothing is ever silently dropped.
    """
    from rich.console import Group

    claimed, approved, variance = _extract_totals(message)
    remainder = _extract_remainder(message)
    warning_items, policy_limits, submit_text = _parse_inline_sections(remainder)

    sections: list[Any] = []

    # ── Totals table ──────────────────────────────────────────────────────────
    totals = Table(box=None, show_header=False, padding=(0, 2))
    totals.add_column("Label", style=f"bold {_T.palette.brand_primary}", width=22)
    totals.add_column("Value", style=f"bold {_T.palette.text_primary}")
    totals.add_row("Claimed Amount", claimed or "—")
    totals.add_row("Approved Amount", approved or "—")
    totals.add_row(
        "Variance",
        f"[{_T.palette.warning}]{variance or '—'}[/]",
    )
    sections.append(Text("Claim Totals", style=f"bold {_T.palette.brand_primary}"))
    sections.append(totals)

    # ── Warnings (bullet list) ────────────────────────────────────────────────
    if warning_items:
        sections.append(Rule(style=_T.palette.border_dim))
        sections.append(Text("Warnings", style=f"bold {_T.palette.warning}"))
        sections.append(Text(""))
        for item in warning_items:
            bullet = Text()
            bullet.append(f"  {_T.icons.bullet} ", style=f"bold {_T.palette.warning}")
            bullet.append(item, style=_T.palette.muted)
            sections.append(bullet)
        sections.append(Text(""))

    # ── Applied Policy Limits (table per category) ────────────────────────────
    if policy_limits:
        sections.append(Rule(style=_T.palette.border_dim))
        sections.append(Text("Applied Policy Limits", style=f"bold {_T.palette.brand_primary}"))
        sections.append(Text(""))
        for pol in policy_limits:
            sections.append(Text(pol.category, style=f"bold {_T.palette.brand_secondary}"))
            if pol.limits:
                lt = Table(box=None, show_header=False, padding=(0, 2))
                lt.add_column("Key", style=_T.text.label, width=20)
                lt.add_column("Value", style=_T.text.value)
                for k, v in pol.limits:
                    lt.add_row(k, v)
                sections.append(lt)
            sections.append(Text(""))

    # ── Submit / confirmation prompt ──────────────────────────────────────────
    if submit_text:
        sections.append(Rule(style=_T.palette.border_dim))
        sections.append(Text(""))
        sections.append(Text(submit_text, style=f"bold {_T.palette.text_primary}"))

    # ── Markdown fallback (when inline parser found nothing) ──────────────────
    elif not warning_items and not policy_limits and remainder.strip():
        sections.append(Rule(style=_T.palette.border_dim))
        sections.append(Markdown(remainder, code_theme="monokai", hyperlinks=False))

    console.print(
        Panel(
            Group(*sections),
            title=f"[bold {_T.palette.brand_primary}]Claim Summary[/]",
            title_align="center",
            border_style=_T.palette.brand_primary,
            box=box.ROUNDED,
            padding=(1, 3),
            expand=True,
        )
    )


# ─── Response renderer ────────────────────────────────────────────────────────


def render_response(message: str) -> None:
    """
    Render the assistant's response.

    If the message is detected as a Claim Summary it is routed to the
    dedicated structured renderer; otherwise it falls back to Markdown.
    """
    if _is_claim_summary(message):
        render_claim_summary(message)
        return

    title = f"[{_T.palette.brand_primary}]Assistant[/]"

    md = Markdown(message, code_theme="monokai", hyperlinks=True)

    console.print(
        Panel(
            md,
            title=title,
            title_align="left",
            border_style=_T.palette.border,
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
    )


# ─── Session footer ───────────────────────────────────────────────────────────


def render_session_footer(session: SessionManager) -> None:
    """
    Render the session statistics footer after each turn.

    Example:
        ────────────────────────────────────────────────────────
        Session 09bc95f4-3208-40ce-8948-3d966ca756f2 │ Turn 12 │ 0.62 s
    """
    _rule()

    latency_str: str = f"{session.last_latency:.2f} s" if session.last_latency is not None else "—"

    stats = Text()
    stats.append(
        f"Session {session.display_session_id} │ Turn {session.turn_count} │ {latency_str}",
        style="dim",
    )

    console.print(stats, no_wrap=True)
    console.print()


# ─── Stage hint ───────────────────────────────────────────────────────────────


def render_stage(stage: str) -> None:
    """Render the conversation_stage value from the runtime as a subtle hint."""
    console.print(f"  [{_T.text.stage}]{_T.icons.arrow} Stage: {stage}[/]")


# ─── Error / warning / success panels ────────────────────────────────────────


def render_error(title: str, message: str, detail: str | None = None) -> None:
    """Render a rich error panel instead of a raw traceback."""
    body = Text()
    body.append(f"{_T.icons.error} {message}", style=f"bold {_T.palette.error}")

    if detail:
        body.append("\n\n")
        body.append(detail, style=_T.palette.muted)

    console.print(
        Panel(
            body,
            title=f"[bold {_T.palette.error}]{title}[/]",
            title_align="left",
            border_style=_T.palette.error,
            box=box.HEAVY,
            padding=(1, 2),
        )
    )


def render_warning(message: str) -> None:
    """Render a warning panel."""
    console.print(
        Panel(
            f"[{_T.palette.warning}]{_T.icons.warning}  {message}[/]",
            border_style=_T.palette.warning,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def render_success(message: str) -> None:
    """Render a success panel."""
    console.print(
        Panel(
            f"[{_T.palette.success}]{_T.icons.success}  {message}[/]",
            border_style=_T.palette.success,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


def render_info(title: str, message: str) -> None:
    """Render a neutral information panel."""
    console.print(
        Panel(
            f"[{_T.palette.brand_secondary}]{_T.icons.info}  {message}[/]",
            title=f"[bold {_T.palette.brand_primary}]{title}[/]",
            title_align="left",
            border_style=_T.palette.brand_secondary,
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )


# ─── JSON renderer ────────────────────────────────────────────────────────────


def render_json(data: Any, title: str = "JSON") -> None:
    """Pretty-print any JSON-serialisable object with syntax highlighting."""
    serialised = _json.dumps(data, indent=2, default=str)
    syntax = Syntax(serialised, "json", theme="monokai", line_numbers=False)
    console.print(
        Panel(
            syntax,
            title=f"[bold {_T.palette.brand_primary}]{title}[/]",
            title_align="left",
            border_style=_T.palette.border,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


# ─── Table renderer ───────────────────────────────────────────────────────────


def render_table(
    headers: list[str],
    rows: list[list[str]],
    title: str = "",
) -> None:
    """Render a generic Rich table."""
    table = Table(
        title=title,
        box=box.ROUNDED,
        border_style=_T.palette.border,
        header_style=f"bold {_T.palette.brand_primary}",
        show_lines=True,
    )

    for header in headers:
        table.add_column(header, style=_T.text.value)

    for row in rows:
        table.add_row(*row)

    console.print(table)


# ─── History renderer ─────────────────────────────────────────────────────────


def render_history(session: SessionManager) -> None:
    """Render all conversation turns as a Rich table."""
    turns = session.turns

    if not turns:
        render_info("History", "No conversation turns recorded yet.")
        return

    table = Table(
        title="[bold bright_white]Conversation History[/]",
        box=box.ROUNDED,
        border_style=_T.palette.border,
        header_style=f"bold {_T.palette.brand_primary}",
        show_lines=True,
        expand=True,
    )

    table.add_column("#", style="bold", width=4, justify="right")
    table.add_column("You", style=_T.text.value, ratio=2)
    table.add_column("Assistant", style=_T.text.value, ratio=4)
    table.add_column("Latency", style=_T.palette.muted, width=10, justify="right")

    for turn in turns:
        user_preview = turn.user_message[:80] + ("…" if len(turn.user_message) > 80 else "")
        asst_preview = turn.assistant_message[:120] + (
            "…" if len(turn.assistant_message) > 120 else ""
        )
        table.add_row(
            str(turn.turn_number),
            user_preview,
            asst_preview,
            f"{turn.latency_seconds:.2f}s",
        )

    console.print(table)


# ─── Blank line helper ────────────────────────────────────────────────────────


def print_blank() -> None:
    """Print a single blank line for spacing."""
    console.print()
