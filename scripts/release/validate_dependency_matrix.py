#!/usr/bin/env python3
"""Validate that runtime dependency pins match the compatibility matrix."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from packaging.requirements import Requirement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyproject", default="pyproject.toml")
    parser.add_argument(
        "--matrix", default="docs/releases/dependency-compatibility-matrix.toml"
    )
    return parser.parse_args()


def load_toml(path: Path) -> Dict[str, object]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def normalize_requirement(raw: str) -> str:
    req = Requirement(raw)
    if req.url:
        return f"url:{req.url}"
    specs = list(req.specifier)
    if len(specs) == 1 and specs[0].operator == "==" and not specs[0].version.endswith(".*"):
        return specs[0].version
    return raw


def runtime_dependencies(pyproject: Dict[str, object]) -> Dict[str, str]:
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project]")
    deps = project.get("dependencies")
    if not isinstance(deps, list):
        raise SystemExit("Invalid pyproject.toml: [project].dependencies must be a list")

    result: Dict[str, str] = {}
    for raw in deps:
        req = Requirement(str(raw))
        if req.name.startswith("spec-kitty-") and req.name != "spec-kitty-runtime":
            result[req.name] = normalize_requirement(str(raw))
    return result


def main() -> int:
    args = parse_args()
    pyproject = load_toml(Path(args.pyproject))
    matrix = load_toml(Path(args.matrix))

    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise SystemExit("Invalid pyproject.toml: missing [project]")

    version = project.get("version")
    if not isinstance(version, str):
        raise SystemExit("Invalid pyproject.toml: missing [project].version")

    runtime = matrix.get("runtime")
    if not isinstance(runtime, dict):
        raise SystemExit("Compatibility matrix missing [runtime] table")

    entry = runtime.get(version)
    if not isinstance(entry, dict):
        raise SystemExit(
            f"Compatibility matrix missing [runtime.\"{version}\"] entry for current version"
        )

    expected = entry.get("dependencies")
    if not isinstance(expected, dict):
        raise SystemExit(
            f"Compatibility matrix entry [runtime.\"{version}\"] must include .dependencies table"
        )

    actual = runtime_dependencies(pyproject)

    issues: List[str] = []
    for package, pinned in actual.items():
        expected_pin = expected.get(package)
        if not isinstance(expected_pin, str):
            issues.append(
                f"Matrix missing expected pin for {package} in [runtime.\"{version}\".dependencies]"
            )
            continue
        if pinned != expected_pin:
            issues.append(
                f"Pin mismatch for {package}: pyproject='{pinned}' vs matrix='{expected_pin}'"
            )

    train = matrix.get("release_train")
    if not isinstance(train, dict) or not isinstance(train.get("order"), list):
        issues.append("Matrix missing [release_train].order list")

    print("Dependency Matrix Summary")
    print("-------------------------")
    print(f"- runtime version: {version}")
    for package, pinned in sorted(actual.items()):
        print(f"- {package}: {pinned}")

    if issues:
        print("\nMatrix validation failures:")
        for idx, issue in enumerate(issues, start=1):
            print(f"  {idx}. {issue}")
        return 1

    print("\nDependency matrix check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
