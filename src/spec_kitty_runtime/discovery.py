"""Mission pack discovery with deterministic precedence."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from spec_kitty_runtime.schema import (
    DiscoveredMission,
    MissionRuntimeError,
    MissionTemplate,
    load_mission_template_file,
)


class DiscoveryContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_dir: Path | None = None
    explicit_paths: list[Path] = Field(default_factory=list)
    env_var_name: str = "SPEC_KITTY_MISSION_PATHS"
    user_home: Path = Field(default_factory=lambda: Path.home())
    builtin_roots: list[Path] = Field(default_factory=list)


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _collect_from_manifest(pack_root: Path) -> list[Path]:
    pack_file = pack_root / "mission-pack.yaml"
    if not pack_file.exists():
        return []
    with open(pack_file, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    paths: list[Path] = []
    entries = raw.get("missions", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, str):
                paths.append(pack_root / entry / "mission.yaml")
            elif isinstance(entry, dict):
                rel = entry.get("path")
                if isinstance(rel, str) and rel.strip():
                    paths.append(pack_root / rel)
    return paths


def _scan_root(root: Path) -> list[Path]:
    candidates: list[Path] = []

    if root.is_file() and root.name == "mission.yaml":
        return [root]

    if not root.exists() or not root.is_dir():
        return []

    # Explicit manifest entries first.
    candidates.extend(_collect_from_manifest(root))

    # Legacy/common mission-root layout: <root>/<mission_key>/mission.yaml
    for mission_file in sorted(root.glob("*/mission.yaml")):
        candidates.append(mission_file)

    # Canonical pack layout.
    missions_dir = root / "missions"
    if missions_dir.is_dir():
        for mission_file in sorted(missions_dir.glob("*/mission.yaml")):
            candidates.append(mission_file)

    # Direct mission root fallback.
    if (root / "mission.yaml").exists():
        candidates.append(root / "mission.yaml")

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def _project_config_pack_paths(project_dir: Path) -> list[Path]:
    config_file = project_dir / ".kittify" / "config.yaml"
    if not config_file.exists():
        return []
    with open(config_file, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    mission_packs = raw.get("mission_packs", [])
    if not isinstance(mission_packs, list):
        return []
    return [project_dir / pack for pack in mission_packs if isinstance(pack, str)]


def discover_missions(context: DiscoveryContext) -> list[DiscoveredMission]:
    """Discover missions by precedence.

    Includes shadowed missions with `selected=False` so callers can surface
    collisions with origin metadata.
    """
    tiers: list[tuple[str, str, list[Path]]] = []

    tiers.append(("explicit", "explicit_paths", context.explicit_paths))

    env_value = os.environ.get(context.env_var_name, "")
    tiers.append(("env", context.env_var_name, _split_env_paths(env_value)))

    project_dir = context.project_dir
    if project_dir:
        tiers.append(
            (
                "project_override",
                str(project_dir / ".kittify" / "overrides" / "missions"),
                [project_dir / ".kittify" / "overrides" / "missions"],
            )
        )
        tiers.append(
            (
                "project_legacy",
                str(project_dir / ".kittify" / "missions"),
                [project_dir / ".kittify" / "missions"],
            )
        )

    tiers.append(
        (
            "user_global",
            str(context.user_home / ".kittify" / "missions"),
            [context.user_home / ".kittify" / "missions"],
        )
    )

    if project_dir:
        tiers.append(
            (
                "project_config",
                str(project_dir / ".kittify" / "config.yaml"),
                _project_config_pack_paths(project_dir),
            )
        )

    tiers.append(("builtin", "builtin_roots", context.builtin_roots))

    discovered: list[DiscoveredMission] = []
    selected_by_key: set[str] = set()

    for tier, origin, roots in tiers:
        for root in roots:
            for mission_yaml in _scan_root(root):
                try:
                    template = load_mission_template_file(mission_yaml)
                except Exception:
                    continue
                key = template.mission.key
                selected = key not in selected_by_key
                if selected:
                    selected_by_key.add(key)
                discovered.append(
                    DiscoveredMission(
                        key=key,
                        path=str(mission_yaml.resolve()),
                        origin=origin,
                        precedence_tier=tier,
                        selected=selected,
                    )
                )

    return discovered


def load_mission_template(path_or_key: str, context: DiscoveryContext | None = None) -> MissionTemplate:
    """Load mission template by explicit path or discovered mission key."""
    candidate_path = Path(path_or_key)

    if candidate_path.exists():
        if candidate_path.is_dir():
            candidate_path = candidate_path / "mission.yaml"
        return load_mission_template_file(candidate_path)

    if context is None:
        context = DiscoveryContext()

    discovered = discover_missions(context)
    for item in discovered:
        if item.key == path_or_key and item.selected:
            return load_mission_template_file(Path(item.path))

    raise MissionRuntimeError(
        f"Mission '{path_or_key}' not found. Checked discovery tiers via context={context.model_dump()}"
    )
