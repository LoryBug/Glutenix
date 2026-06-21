"""Validate generated documentation against structured literature data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from glutenix.calibration.literature import load_literature_sources
from glutenix.calibration.literature import validate_literature_source_references
from scripts.generate_bibliography import DEFAULT_OUTPUT as BIBLIOGRAPHY_OUTPUT
from scripts.generate_bibliography import render_bibliography
from scripts.generate_evidence_summary import planned_outputs


def validate_docs() -> list[str]:
    errors: list[str] = []
    try:
        validate_literature_source_references()
    except Exception as exc:  # noqa: BLE001 - command should report all validation failures clearly.
        errors.append(f"source registry validation failed: {exc}")

    expected_bibliography = render_bibliography(load_literature_sources())
    if not BIBLIOGRAPHY_OUTPUT.exists():
        errors.append(f"missing generated bibliography: {BIBLIOGRAPHY_OUTPUT.relative_to(PROJECT_ROOT)}")
    elif BIBLIOGRAPHY_OUTPUT.read_text(encoding="utf-8") != expected_bibliography:
        errors.append("generated bibliography is stale")

    for path, expected in planned_outputs().items():
        if not path.exists():
            errors.append(f"missing generated evidence output: {path.relative_to(PROJECT_ROOT)}")
        elif path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated evidence output is stale: {path.relative_to(PROJECT_ROOT)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    errors = validate_docs()
    if errors:
        print("Documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        print("Run:")
        print("  uv run python scripts/generate_bibliography.py")
        print("  uv run python scripts/generate_evidence_summary.py")
        return 1
    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
