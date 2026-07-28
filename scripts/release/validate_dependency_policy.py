#!/usr/bin/env python3
"""Validate spec-kitty-runtime dependency policy before publishing.

Accepted shapes for a shared ``spec-kitty-*`` dependency:

* an **exact pin** (``==X.Y.Z``), or
* a **bounded range** with both a lower and an upper bound (``>=3.0,<7.0``).

An unbounded specifier (``>=6.0.0`` alone), a bare package name, or a direct
URL reference are all rejected — the last unless explicitly approved. A range
with an explicit prerelease bound also requires ``--allow-prerelease``.

Bounded ranges are accepted because this package is a *library* installed into
shared environments alongside other consumers of the same contract package. An
exact pin in a library is a diamond-dependency generator: ``spec-kitty-runtime``
0.4.5 pinned ``spec-kitty-events==3.3.0`` while the CLI required
``>=6.0.0,<7.0.0``, so co-installing them silently backtracked the CLI three
major versions rather than failing. See Priivacy-ai/spec-kitty-runtime#21.

Licence assurance is preserved and is strictly stronger for a range than for an
exact pin: *every* installable, non-yanked release the range admits must carry
clear MIT metadata, not just the single pinned one. A range that matches no
installable release is also rejected, which is the check the ``==`` path used
to get for free from a 404.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--libraries",
        default="spec-kitty-events",
        help="Comma-separated dependency names to validate.",
    )
    parser.add_argument(
        "--allow-prerelease",
        action="store_true",
        help="Allow prerelease dependency pins for this run.",
    )
    parser.add_argument(
        "--allow-direct-reference",
        action="store_true",
        help="Allow direct-reference dependencies for this run.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow libraries not present in dependency list.",
    )
    parser.add_argument(
        "--skip-pypi-check",
        action="store_true",
        help="Skip PyPI fetch and MIT license validation (for PR-time runs where the pinned version may not be published yet).",
    )
    return parser.parse_args()


def load_dependencies(pyproject_path: Path) -> List[str]:
    if not pyproject_path.exists():
        raise SystemExit(f"pyproject.toml not found: {pyproject_path}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")
    return [str(dep) for dep in deps]


def parse_requirement(raw: str) -> Optional[Requirement]:
    try:
        return Requirement(raw)
    except Exception:
        return None


def lookup_dependency(dependencies: List[str], package: str) -> List[str]:
    matches: List[str] = []
    for dep in dependencies:
        req = parse_requirement(dep)
        if req and req.name.lower() == package.lower():
            matches.append(dep)
            continue
        if dep.lower().startswith(f"{package.lower()} "):
            matches.append(dep)
    return matches


def exact_pin(req: Requirement) -> Optional[str]:
    specs = list(req.specifier)
    if len(specs) != 1:
        return None
    spec = specs[0]
    if spec.operator != "==" or spec.version.endswith(".*"):
        return None
    return spec.version


_LOWER_BOUND_OPERATORS = {">=", ">", "~="}
_UPPER_BOUND_OPERATORS = {"<", "<="}


def bounded_range(req: Requirement) -> Optional[str]:
    """Return the normalized specifier iff it is a *bounded* range.

    A bounded range has at least one lower bound and at least one upper bound,
    and contains no ``==`` clause. ``>=6.0.0`` alone is NOT bounded: it silently
    accepts every future major, which is the failure mode an exact pin was
    protecting against. ``>=6.0.0,<7.0.0`` is.

    Returns the ``str(SpecifierSet)`` form, which ``packaging`` renders in a
    stable sorted order, so it can be compared byte-for-byte against the
    compatibility matrix.
    """
    specs = list(req.specifier)
    if not specs:
        return None
    if any(spec.operator in {"==", "==="} for spec in specs):
        return None
    has_lower = any(spec.operator in _LOWER_BOUND_OPERATORS for spec in specs)
    has_upper = any(spec.operator in _UPPER_BOUND_OPERATORS for spec in specs)
    if not (has_lower and has_upper):
        return None
    return str(req.specifier)


def fetch_pypi_releases(package: str) -> Dict[str, object]:
    """Return the full PyPI release index for ``package``."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(f"Package not found on PyPI: {package}")
        raise
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach PyPI for {package}: {exc}") from exc

    releases = payload.get("releases")
    if not isinstance(releases, dict):
        raise SystemExit(f"Unexpected PyPI payload for {package}")
    return releases


def versions_satisfying(package: str, req: Requirement) -> List[str]:
    """Installable, non-yanked releases matching ``req``.

    An empty result means the declared range is unsatisfiable against what is
    actually published — the failure the ``==`` path used to get for free from
    a 404 on the per-version PyPI endpoint. ``SpecifierSet`` owns prerelease
    filtering: ordinary stable ranges exclude them, while a range with an
    explicit prerelease bound includes them after ``main`` verifies the
    ``--allow-prerelease`` approval.
    """
    releases = fetch_pypi_releases(package)
    candidates: List[str] = []
    for raw_version, files in releases.items():
        try:
            parsed = Version(raw_version)
        except InvalidVersion:
            continue
        if not isinstance(files, list) or not files:
            continue
        if all(f.get("yanked") for f in files):
            continue
        if parsed in req.specifier:
            candidates.append(raw_version)
    return sorted(candidates, key=Version)


def fetch_pypi_info(package: str, version: str) -> Dict[str, object]:
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(f"Pinned version not found on PyPI: {package}=={version}")
        raise
    except urllib.error.URLError as exc:
        raise SystemExit(f"Unable to reach PyPI for {package}=={version}: {exc}") from exc

    info = payload.get("info")
    if not isinstance(info, dict):
        raise SystemExit(f"Unexpected PyPI payload for {package}=={version}")
    return info


def has_mit_metadata(info: Dict[str, object]) -> bool:
    classifiers = info.get("classifiers")
    classifier_ok = isinstance(classifiers, list) and any(
        isinstance(c, str) and c.strip() == "License :: OSI Approved :: MIT License"
        for c in classifiers
    )
    license_field = info.get("license")
    license_expr = info.get("license_expression")
    license_ok = isinstance(license_field, str) and "mit" in license_field.lower()
    license_expr_ok = isinstance(license_expr, str) and "mit" in license_expr.lower()
    return classifier_ok or license_ok or license_expr_ok


def main() -> int:
    args = parse_args()
    dependencies = load_dependencies(Path(args.pyproject))
    libraries = [lib.strip() for lib in args.libraries.split(",") if lib.strip()]

    issues: List[str] = []
    summary: List[str] = []

    for library in libraries:
        matches = lookup_dependency(dependencies, library)
        if not matches:
            if not args.allow_missing:
                issues.append(f"Missing required dependency pin for {library}.")
            continue

        if len(matches) > 1:
            issues.append(f"Multiple dependency entries for {library}: {matches}")
            continue

        req = parse_requirement(matches[0])
        if req is None:
            issues.append(f"Unable to parse dependency requirement: {matches[0]}")
            continue

        if req.url:
            if args.allow_direct_reference:
                summary.append(f"{library}: direct reference approved ({req.url})")
                continue
            issues.append(
                f"{library}: direct reference is not allowed ({matches[0]})."
            )
            continue

        pinned = exact_pin(req)
        ranged = None if pinned else bounded_range(req)

        if not pinned and not ranged:
            issues.append(
                f"{library}: dependency must be exact-pinned with == or declare a "
                f"bounded range with both a lower and an upper bound, e.g. "
                f"'>=3.0,<7.0' (found: {matches[0]})."
            )
            continue

        if ranged and req.specifier.prereleases and not args.allow_prerelease:
            issues.append(
                f"{library}: prerelease range '{ranged}' is not allowed without "
                "explicit approval."
            )
            continue

        if pinned:
            try:
                parsed = Version(pinned)
            except InvalidVersion:
                issues.append(f"{library}: invalid pinned version '{pinned}'.")
                continue

            if parsed.is_prerelease and not args.allow_prerelease:
                issues.append(
                    f"{library}: prerelease pin '{pinned}' is not allowed without explicit approval."
                )

            if args.skip_pypi_check:
                summary.append(f"{library}: validated {pinned} (PyPI check skipped)")
                continue

            try:
                info = fetch_pypi_info(library, pinned)
            except SystemExit as exc:
                issues.append(str(exc))
                continue
            if not has_mit_metadata(info):
                issues.append(
                    f"{library}=={pinned}: missing clear MIT metadata on PyPI "
                    "(classifier/license/license_expression)."
                )

            summary.append(f"{library}: validated {pinned}")
            continue

        # Bounded range. Licence assurance is *stronger* here than for an exact
        # pin: every published version a consumer could resolve to must be
        # MIT-clear, not just one.
        if args.skip_pypi_check:
            summary.append(f"{library}: validated range {ranged} (PyPI check skipped)")
            continue

        try:
            in_range = versions_satisfying(library, req)
        except SystemExit as exc:
            issues.append(str(exc))
            continue

        if not in_range:
            issues.append(
                f"{library}: declared range {ranged} matches no installable, "
                f"non-yanked release on PyPI."
            )
            continue

        unlicensed: List[str] = []
        metadata_failed = False
        for candidate in in_range:
            try:
                info = fetch_pypi_info(library, candidate)
            except SystemExit as exc:
                issues.append(str(exc))
                metadata_failed = True
                continue
            if not has_mit_metadata(info):
                unlicensed.append(candidate)

        if metadata_failed:
            continue

        if unlicensed:
            issues.append(
                f"{library}: range {ranged} admits version(s) without clear MIT "
                f"metadata on PyPI: {', '.join(unlicensed)}. Narrow the range to "
                f"exclude them."
            )
            continue

        summary.append(
            f"{library}: validated range {ranged} "
            f"({len(in_range)} MIT-clear releases: {in_range[0]}..{in_range[-1]})"
        )

    print("Dependency Policy Summary")
    print("-------------------------")
    for line in summary:
        print(f"- {line}")

    if issues:
        print("\nDependency policy violations:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nAll dependency policy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
