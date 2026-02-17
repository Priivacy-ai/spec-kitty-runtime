"""Prompt rendering helpers for NextDecision payloads."""

from __future__ import annotations

import json

from spec_kitty_runtime.schema import NextDecision


def render_prompt(decision: NextDecision, format: str = "markdown") -> str:
    """Render a user-facing prompt for a next-decision payload."""
    if format not in {"markdown", "json"}:
        raise ValueError(f"Unsupported prompt format: {format}")

    if format == "json":
        return json.dumps(decision.model_dump(mode="json"), indent=2, sort_keys=True, default=str)

    if decision.kind == "step":
        context = decision.context.model_dump() if decision.context else {}
        return "\n".join(
            [
                f"# Next Step: {decision.step_title or decision.step_id}",
                "",
                decision.prompt or "",
                "",
                "## Context",
                "```json",
                json.dumps(context, indent=2, sort_keys=True),
                "```",
                "",
                "After completion, run `next()` again.",
            ]
        )

    if decision.kind == "decision_required":
        lines = [
            "# Decision Required",
            "",
            decision.question or "A mission decision is required before proceeding.",
        ]
        if decision.options:
            lines.append("")
            lines.append("## Options")
            lines.append("")
            for i, option in enumerate(decision.options, 1):
                lines.append(f"{i}. {option}")
        lines.append("")
        lines.append("Provide an answer, persist it, then run `next()` again.")
        return "\n".join(lines)

    if decision.kind == "blocked":
        return "\n".join(
            [
                "# Mission Blocked",
                "",
                decision.reason or "Mission is blocked.",
                "",
                "Resolve the blocker, then run `next()` again.",
            ]
        )

    return "\n".join(
        [
            "# Mission Complete",
            "",
            decision.reason or "No runnable steps remain.",
        ]
    )
