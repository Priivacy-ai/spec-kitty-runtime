"""Pin-shape rules for the release dependency gate.

Regression cover for Priivacy-ai/spec-kitty-runtime#21: the gate used to accept
*only* ``==X.Y.Z``, which made this library's exact ``spec-kitty-events==3.3.0``
pin unfixable — widening it would have failed the release. A bounded range is
now accepted; an unbounded one still is not.

These tests are offline. They exercise pin-shape classification and mock the
PyPI release and metadata boundaries so failure paths remain covered even when
PR-time CI deliberately skips live network checks.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from packaging.requirements import Requirement

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release" / "validate_dependency_policy.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("validate_dependency_policy", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = _load()


# ---------------------------------------------------------------------------
# Accepted shapes
# ---------------------------------------------------------------------------


def test_exact_pin_still_accepted() -> None:
    """The historical shape must keep working — other pins rely on it."""
    assert policy.exact_pin(Requirement("spec-kitty-events==3.3.0")) == "3.3.0"
    assert policy.bounded_range(Requirement("spec-kitty-events==3.3.0")) is None


def test_bounded_range_accepted_and_normalized() -> None:
    """A range with both bounds is accepted and rendered in stable order."""
    assert policy.bounded_range(Requirement("spec-kitty-events>=3.0,<7.0")) == "<7.0,>=3.0"
    # Written the other way round, it normalizes identically — this is what
    # makes byte-comparison against the compatibility matrix safe.
    assert policy.bounded_range(Requirement("spec-kitty-events<7.0,>=3.0")) == "<7.0,>=3.0"


def test_inclusive_upper_bound_accepted() -> None:
    assert policy.bounded_range(Requirement("pkg>=1.0,<=2.0")) == "<=2.0,>=1.0"


# ---------------------------------------------------------------------------
# Rejected shapes — the point of the gate
# ---------------------------------------------------------------------------


def test_unbounded_lower_only_rejected() -> None:
    """``>=6.0.0`` alone silently accepts every future major. Still rejected."""
    assert policy.bounded_range(Requirement("spec-kitty-events>=6.0.0")) is None
    assert policy.exact_pin(Requirement("spec-kitty-events>=6.0.0")) is None


def test_unbounded_upper_only_rejected() -> None:
    assert policy.bounded_range(Requirement("pkg<7.0")) is None


def test_bare_package_rejected() -> None:
    assert policy.bounded_range(Requirement("spec-kitty-events")) is None
    assert policy.exact_pin(Requirement("spec-kitty-events")) is None


def test_wildcard_equality_rejected() -> None:
    """``==3.*`` is neither an exact pin nor a bounded range."""
    assert policy.exact_pin(Requirement("pkg==3.*")) is None
    assert policy.bounded_range(Requirement("pkg==3.*")) is None


def test_mixed_equality_and_range_rejected() -> None:
    """An ``==`` clause inside a range is contradictory; do not silently accept."""
    assert policy.bounded_range(Requirement("pkg>=1.0,<2.0,==1.5")) is None


# ---------------------------------------------------------------------------
# The specific regression
# ---------------------------------------------------------------------------


def test_this_packages_own_pin_is_an_accepted_shape() -> None:
    """The pin in pyproject.toml must satisfy the gate this script enforces."""
    import tomllib

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    events = [d for d in data["project"]["dependencies"] if d.startswith("spec-kitty-events")]
    assert len(events) == 1, f"expected exactly one spec-kitty-events entry, got {events}"

    req = Requirement(events[0])
    assert policy.exact_pin(req) or policy.bounded_range(req), (
        f"pyproject.toml declares {events[0]!r}, which the release gate rejects."
    )


def test_declared_range_admits_the_cli_contract() -> None:
    """The range must intersect what spec-kitty-cli requires.

    This is the actual bug: 0.4.5 pinned ``==3.3.0`` while the CLI required
    ``>=6.0.0,<7.0.0``, so no single resolution satisfied both and the resolver
    backtracked the CLI to 0.14.2 instead of erroring.
    """
    import tomllib

    from packaging.version import Version

    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    ours = Requirement(
        next(d for d in data["project"]["dependencies"] if d.startswith("spec-kitty-events"))
    ).specifier
    cli = Requirement("spec-kitty-events>=6.0.0,<7.0.0").specifier

    overlap = [v for v in ("6.0.0", "6.1.0") if Version(v) in ours and Version(v) in cli]
    assert overlap, (
        "The declared spec-kitty-events range does not intersect the CLI's "
        ">=6.0.0,<7.0.0 requirement, so co-installing the two packages cannot "
        "resolve to a shared events version."
    )


# ---------------------------------------------------------------------------
# Range release and licence verification
# ---------------------------------------------------------------------------


def _policy_pyproject(tmp_path: Path, requirement: str) -> Path:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "policy-test"\n'
        'version = "0.0.0"\n'
        f'dependencies = ["{requirement}"]\n',
        encoding="utf-8",
    )
    return pyproject


def _run_policy_main(
    monkeypatch: object,
    pyproject: Path,
    *extra_args: str,
) -> int:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_dependency_policy.py",
            "--pyproject",
            str(pyproject),
            *extra_args,
        ],
    )
    return policy.main()


def test_versions_satisfying_filters_yanked_and_fileless_releases(monkeypatch) -> None:
    """Only installable, non-yanked releases admitted by the range are checked."""
    monkeypatch.setattr(
        policy,
        "fetch_pypi_releases",
        lambda _package: {
            "not-a-version": [{"yanked": False}],
            "6.0.0rc1": [{"yanked": False}],
            "6.0.0": [{"yanked": True}],
            "6.1.0": [],
            "6.2.0": [{"yanked": False}],
        },
    )
    requirement = Requirement("pkg>=6.0.0rc1,<7")
    assert policy.versions_satisfying("pkg", requirement) == ["6.0.0rc1", "6.2.0"]


def test_prerelease_range_requires_explicit_approval(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """A prerelease bound cannot bypass the existing approval policy."""
    pyproject = _policy_pyproject(
        tmp_path,
        "spec-kitty-events>=6.2.0rc1,<7",
    )
    assert _run_policy_main(monkeypatch, pyproject) == 1
    assert "prerelease range" in capsys.readouterr().out


def test_range_matching_no_installable_release_is_rejected(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    pyproject = _policy_pyproject(tmp_path, "spec-kitty-events>=3.0,<7")
    monkeypatch.setattr(policy, "versions_satisfying", lambda _package, _req: [])
    assert _run_policy_main(monkeypatch, pyproject) == 1
    assert "matches no installable, non-yanked release" in capsys.readouterr().out


def test_every_release_in_range_must_be_mit_clear(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    pyproject = _policy_pyproject(tmp_path, "spec-kitty-events>=3.0,<7")
    monkeypatch.setattr(
        policy,
        "versions_satisfying",
        lambda _package, _req: ["3.0.0", "6.1.0"],
    )
    monkeypatch.setattr(
        policy,
        "fetch_pypi_info",
        lambda _package, version: {
            "license": "MIT" if version == "3.0.0" else "Apache-2.0"
        },
    )
    assert _run_policy_main(monkeypatch, pyproject) == 1
    assert "without clear MIT metadata on PyPI: 6.1.0" in capsys.readouterr().out


def test_mit_clear_range_passes_end_to_end(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    pyproject = _policy_pyproject(tmp_path, "spec-kitty-events>=3.0,<7")
    monkeypatch.setattr(
        policy,
        "versions_satisfying",
        lambda _package, _req: ["3.0.0", "6.1.0"],
    )
    monkeypatch.setattr(
        policy,
        "fetch_pypi_info",
        lambda _package, _version: {"license_expression": "MIT"},
    )
    assert _run_policy_main(monkeypatch, pyproject) == 0
    output = capsys.readouterr().out
    assert "2 MIT-clear releases: 3.0.0..6.1.0" in output
    assert "All dependency policy checks passed." in output


def test_malformed_release_index_is_rejected(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """An unexpected PyPI index shape must fail the release gate."""
    pyproject = _policy_pyproject(tmp_path, "spec-kitty-events>=3.0,<7")

    def fail_index(_package, _req):
        raise SystemExit("Unexpected PyPI payload for spec-kitty-events")

    monkeypatch.setattr(policy, "versions_satisfying", fail_index)
    assert _run_policy_main(monkeypatch, pyproject) == 1
    assert "Unexpected PyPI payload" in capsys.readouterr().out


def test_metadata_network_failure_is_rejected_without_success_summary(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """A failed per-version fetch cannot also report the range as validated."""
    pyproject = _policy_pyproject(tmp_path, "spec-kitty-events>=3.0,<7")
    monkeypatch.setattr(
        policy,
        "versions_satisfying",
        lambda _package, _req: ["6.1.0"],
    )

    def fail_metadata(_package, _version):
        raise SystemExit("Unable to reach PyPI for spec-kitty-events==6.1.0")

    monkeypatch.setattr(policy, "fetch_pypi_info", fail_metadata)
    assert _run_policy_main(monkeypatch, pyproject) == 1
    output = capsys.readouterr().out
    assert "Unable to reach PyPI" in output
    assert "validated range" not in output
