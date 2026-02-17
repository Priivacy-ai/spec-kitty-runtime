"""Host-agnostic capability bindings for mission runtime context."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CapabilityBindings(BaseModel):
    """Portable capability envelope for skills/agents/connections."""

    model_config = ConfigDict(frozen=True)

    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    connections: list[str] = Field(default_factory=list)


def from_payload(payload: dict | None) -> CapabilityBindings:
    """Create bindings from loose payload data."""
    payload = payload or {}
    return CapabilityBindings(
        skills=list(payload.get("skills", []) or []),
        agents=list(payload.get("agents", []) or []),
        connections=list(payload.get("connections", []) or []),
    )
