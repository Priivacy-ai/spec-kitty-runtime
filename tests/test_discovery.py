"""Tests for mission discovery with precedence tiers and shadowing diagnostics."""

import pytest
from pathlib import Path

from spec_kitty_runtime.discovery import DiscoveryContext, diagnose_shadowing, discover_missions
from spec_kitty_runtime.schema import MissionRuntimeError


MISSION_DOC = """\
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


def _write_mission(path: Path, key: str = "software-dev") -> None:
    doc = MISSION_DOC.replace("key: software-dev", f"key: {key}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


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


def test_all_seven_tiers_in_order(monkeypatch, tmp_path: Path) -> None:
    """Set up missions in all 7 tiers and verify correct precedence."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)

    project = tmp_path / "project"
    user_home = tmp_path / "home"

    # Tier 1: explicit
    _write_mission(tmp_path / "explicit" / "software-dev" / "mission.yaml", "tier-explicit")

    # Tier 2: env
    env_root = tmp_path / "env-root"
    _write_mission(env_root / "software-dev" / "mission.yaml", "tier-env")
    monkeypatch.setenv("SPEC_KITTY_MISSION_PATHS", str(env_root))

    # Tier 3: project_override
    _write_mission(
        project / ".kittify" / "overrides" / "missions" / "software-dev" / "mission.yaml",
        "tier-override",
    )

    # Tier 4: project_legacy
    _write_mission(
        project / ".kittify" / "missions" / "software-dev" / "mission.yaml",
        "tier-legacy",
    )

    # Tier 5: user_global
    _write_mission(
        user_home / ".kittify" / "missions" / "software-dev" / "mission.yaml",
        "tier-user-global",
    )

    # Tier 6: project_config
    config_pack_root = tmp_path / "config-pack"
    _write_mission(config_pack_root / "software-dev" / "mission.yaml", "tier-config")
    config_dir = project / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        f"mission_packs:\n  - {config_pack_root}\n",
        encoding="utf-8",
    )

    # Tier 7: builtin
    builtin_root = tmp_path / "builtin"
    _write_mission(builtin_root / "software-dev" / "mission.yaml", "tier-builtin")

    context = DiscoveryContext(
        project_dir=project,
        explicit_paths=[tmp_path / "explicit"],
        user_home=user_home,
        builtin_roots=[builtin_root],
    )

    discovered = discover_missions(context)
    tiers = [d.precedence_tier for d in discovered if d.selected]

    assert "explicit" in tiers
    assert "env" in tiers
    assert "project_override" in tiers
    assert "project_legacy" in tiers
    assert "user_global" in tiers
    assert "project_config" in tiers
    assert "builtin" in tiers


def test_shadowing_diagnostics_structure(monkeypatch, tmp_path: Path) -> None:
    """Verify ShadowEntry fields in diagnostics."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)

    explicit = tmp_path / "explicit" / "software-dev" / "mission.yaml"
    legacy = tmp_path / "project" / ".kittify" / "missions" / "software-dev" / "mission.yaml"

    _write_mission(explicit)
    _write_mission(legacy)

    context = DiscoveryContext(
        project_dir=tmp_path / "project",
        explicit_paths=[tmp_path / "explicit"],
        builtin_roots=[],
    )

    diag = diagnose_shadowing(context)
    assert diag.total_discovered >= 2
    assert diag.total_shadowed >= 1

    entry = next(e for e in diag.entries if e.key == "software-dev")
    assert entry.selected_tier == "explicit"
    assert len(entry.shadowed) >= 1
    assert entry.shadowed[0].selected is False


def test_diagnose_shadowing_counts(monkeypatch, tmp_path: Path) -> None:
    """Shadowing counts are correct."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)

    # Two copies of the same key + one unique key.
    _write_mission(tmp_path / "explicit" / "alpha" / "mission.yaml", "alpha")
    _write_mission(tmp_path / "builtin" / "alpha" / "mission.yaml", "alpha")
    _write_mission(tmp_path / "explicit" / "beta" / "mission.yaml", "beta")

    context = DiscoveryContext(
        explicit_paths=[tmp_path / "explicit"],
        builtin_roots=[tmp_path / "builtin"],
    )

    diag = diagnose_shadowing(context)
    assert diag.total_discovered == 3  # 2 alpha + 1 beta
    assert diag.total_shadowed == 1   # 1 alpha shadowed


def test_mission_pack_manifest_validation(tmp_path: Path) -> None:
    """Invalid pack YAML raises MissionRuntimeError."""
    pack_dir = tmp_path / "bad-pack"
    pack_dir.mkdir()
    # Missing 'pack' section entirely.
    (pack_dir / "mission-pack.yaml").write_text(
        "missions:\n  - key: x\n    path: x/mission.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(MissionRuntimeError, match="missing required 'pack' section"):
        discover_missions(
            DiscoveryContext(explicit_paths=[pack_dir], builtin_roots=[])
        )


# ---------------------------------------------------------------------------
# P2: Discovery warnings (not silent swallowing)
# ---------------------------------------------------------------------------

def test_discover_missions_with_warnings_surfaces_load_errors(monkeypatch, tmp_path: Path) -> None:
    """Invalid mission YAML is reported as a warning, not silently dropped."""
    from spec_kitty_runtime.discovery import discover_missions_with_warnings

    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)

    # Write a valid mission.
    _write_mission(tmp_path / "pack" / "good" / "mission.yaml", "good")

    # Write an invalid mission (no steps).
    bad_dir = tmp_path / "pack" / "bad"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "mission.yaml").write_text(
        "mission:\n  key: bad\n  name: Bad\n  version: 1.0.0\nsteps: []\n",
        encoding="utf-8",
    )

    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    result = discover_missions_with_warnings(context)

    # Good mission discovered.
    assert any(m.key == "good" for m in result.missions)

    # Bad mission reported as warning.
    assert len(result.warnings) >= 1
    bad_warnings = [w for w in result.warnings if "bad" in w.path.lower() or "no steps" in w.error.lower()]
    assert len(bad_warnings) >= 1
    assert "no steps" in bad_warnings[0].error.lower()


def test_discover_missions_still_works_with_invalid_files(monkeypatch, tmp_path: Path) -> None:
    """discover_missions() (backward-compat) skips bad files but still returns good ones."""
    monkeypatch.delenv("SPEC_KITTY_MISSION_PATHS", raising=False)

    _write_mission(tmp_path / "pack" / "good" / "mission.yaml", "good")

    bad_dir = tmp_path / "pack" / "bad"
    bad_dir.mkdir(parents=True, exist_ok=True)
    (bad_dir / "mission.yaml").write_text("not: valid: yaml: {{{{", encoding="utf-8")

    context = DiscoveryContext(explicit_paths=[tmp_path / "pack"], builtin_roots=[])
    discovered = discover_missions(context)

    assert any(m.key == "good" for m in discovered)
    assert not any(m.key == "bad" for m in discovered)
