"""Host-agnostic capability bindings for mission runtime context."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class UserConnection(BaseModel):
    """A per-user connection to an external provider."""

    model_config = ConfigDict(frozen=True)

    connection_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    is_active: bool = True


@runtime_checkable
class CapabilityAdapter(Protocol):
    """Protocol for resolving host capabilities at runtime."""

    @property
    def adapter_id(self) -> str: ...

    def list_skills(self) -> list[str]: ...

    def list_agents(self) -> list[str]: ...

    def list_connections(self, *, user_id: str | None = None) -> list[UserConnection]: ...

    def resolve_skill(self, name: str) -> dict[str, Any]: ...

    def resolve_agent(self, name: str) -> dict[str, Any]: ...


class CapabilityBindings(BaseModel):
    """Portable capability envelope for skills/agents/connections."""

    model_config = ConfigDict(frozen=True)

    skills: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    connections: list[UserConnection] = Field(default_factory=list)


def from_payload(payload: dict | None) -> CapabilityBindings:
    """Create bindings from loose payload data."""
    payload = payload or {}
    raw_connections = payload.get("connections", []) or []
    connections: list[UserConnection] = []
    for item in raw_connections:
        if isinstance(item, str):
            # Legacy format: plain connection_id string
            connections.append(UserConnection(
                connection_id=item, user_id="unknown", provider="unknown",
            ))
        elif isinstance(item, dict):
            connections.append(UserConnection(**item))
    return CapabilityBindings(
        skills=list(payload.get("skills", []) or []),
        agents=list(payload.get("agents", []) or []),
        connections=connections,
    )
