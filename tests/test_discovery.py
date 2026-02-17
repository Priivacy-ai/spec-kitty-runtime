from pathlib import Path

from spec_kitty_runtime.discovery import DiscoveryContext, discover_missions


MISSION_DOC = """
mission:
  key: software-dev
  name: Software Development
  version: 1.0.0
  description: Test mission
steps:
  - id: S1
    title: First Step
    prompt: Do first thing
"""


def _write_mission(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MISSION_DOC, encoding="utf-8")


def test_discovery_reports_shadowing(monkeypatch, tmp_path: Path) -> None:
    explicit = tmp_path / "explicit" / "missions" / "software-dev" / "mission.yaml"
    legacy = tmp_path / "project" / ".kittify" / "missions" / "software-dev" / "mission.yaml"

    _write_mission(explicit)
    _write_mission(legacy)

    context = DiscoveryContext(
        project_dir=tmp_path / "project",
        explicit_paths=[tmp_path / "explicit"],
        builtin_roots=[],
    )

    discovered = discover_missions(context)
    candidates = [item for item in discovered if item.key == "software-dev"]

    assert len(candidates) >= 2
    assert candidates[0].selected is True
    assert candidates[0].precedence_tier == "explicit"
    assert any(item.selected is False for item in candidates[1:])
