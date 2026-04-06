#!/usr/bin/env python3
"""Validate spec-kitty-runtime dependency policy before publishing."""

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
        if not pinned:
            issues.append(
                f"{library}: dependency must be exact-pinned with == (found: {matches[0]})."
            )
            continue

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
        else:
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
