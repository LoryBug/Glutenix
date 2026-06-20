"""Update generated calibration-report sections.

The generated blocks are intentionally limited to tables and dataset summaries.
Interpretation, limitations, and scientific conclusions remain hand-authored.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from glutenix.calibration.literature import compare_bread_baking_records
from glutenix.db.base import Base
from glutenix.db.seed import _seed_applications, _seed_ingredients


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BREAD_REPORT = PROJECT_ROOT / "docs" / "bread-baking-calibration-report.md"

BREAD_START = "<!-- generated-start: bread-calibration-summary -->"
BREAD_END = "<!-- generated-end: bread-calibration-summary -->"


def _seeded_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    _seed_ingredients(session)
    _seed_applications(session)
    session.commit()
    return session


def _cell(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)


def _metric_count(rows: list[dict[str, Any]], measured_key: str) -> int:
    return sum(row.get(measured_key) is not None for row in rows)


def _render_bread_block(result: dict[str, Any]) -> str:
    rows = result["rows"]
    metric_specs = [
        ("specific_volume_cm3_g", "measured_specific_volume_cm3_g"),
        ("crumb_hardness_n", "measured_crumb_hardness_n"),
        ("porosity_pct", "measured_porosity_pct"),
    ]

    lines: list[str] = [
        BREAD_START,
        "## Dataset",
        "",
        f"Records: {result['n_records']}",
        "",
        f"Sources: {result['source_count']}",
        "",
        f"Main metric: `{result['metric']}`",
        "",
        "Auxiliary metrics where available:",
        "",
        "- `crumb_hardness_n`",
        "- `bake_loss_pct`",
        "- `moisture_pct`",
        "- `water_activity`",
        "- `void_fraction_pct`",
        "- `porosity_pct`",
        "- TPA fields from Loncaric 2026",
        "",
        "Coverage by process family:",
        "",
        "| Process family | Records |",
        "|---|---:|",
    ]

    for family, count in sorted(result["record_groups"]["process_family"].items()):
        lines.append(f"| `{family}` | {count} |")

    lines.extend([
        "",
        "## Error Summary",
        "",
        "| Metric | Records | MAE | RMSE | Bias |",
        "|---|---:|---:|---:|---:|",
    ])

    for metric, measured_key in metric_specs:
        summary = result["metric_summaries"].get(metric)
        if not summary:
            continue
        count = _metric_count(rows, measured_key)
        lines.append(
            f"| `{metric}` | {count} | {summary['mae']} | {summary['rmse']} | {summary['bias']} |"
        )

    lines.extend([
        "",
        "## Record Groups",
        "",
        "By process family:",
        "",
        "| Process family | Records |",
        "|---|---:|",
    ])

    for family, count in sorted(result["record_groups"]["process_family"].items()):
        lines.append(f"| `{family}` | {count} |")

    lines.extend([
        "",
        "By source:",
        "",
        "| Source | Records |",
        "|---|---:|",
    ])

    for source, count in sorted(result["record_groups"]["source"].items()):
        lines.append(f"| `{source}` | {count} |")

    lines.extend([
        "",
        "## Rows",
        "",
        "| ID | Measured volume | Simulated volume | Measured hardness | Simulated hardness | Measured porosity | Simulated porosity | Process family |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ])

    for row in rows:
        lines.append(
            "| "
            f"`{row['id']}` | "
            f"{_cell(row.get('measured_specific_volume_cm3_g'))} | "
            f"{_cell(row.get('simulated_specific_volume_cm3_g'))} | "
            f"{_cell(row.get('measured_crumb_hardness_n'))} | "
            f"{_cell(row.get('simulated_crumb_hardness_n'))} | "
            f"{_cell(row.get('measured_porosity_pct'))} | "
            f"{_cell(row.get('simulated_porosity_pct'))} | "
            f"`{row['process_family']}` |"
        )

    lines.extend(["", BREAD_END])
    return "\n".join(lines)


def _replace_block(document: str, start: str, end: str, replacement: str) -> str:
    start_index = document.find(start)
    end_index = document.find(end)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise ValueError(f"Could not find generated block markers: {start} / {end}")
    end_index += len(end)
    return document[:start_index] + replacement + document[end_index:]


def update_bread_report(*, write: bool) -> bool:
    session = _seeded_session()
    try:
        result = compare_bread_baking_records(session)
    finally:
        session.close()

    current = BREAD_REPORT.read_text(encoding="utf-8")
    updated = _replace_block(current, BREAD_START, BREAD_END, _render_bread_block(result))

    if current == updated:
        return False
    if write:
        BREAD_REPORT.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Update files in place.")
    parser.add_argument("--check", action="store_true", help="Fail if generated sections are stale.")
    args = parser.parse_args()

    if args.write and args.check:
        parser.error("Use either --write or --check, not both.")
    if not args.write and not args.check:
        parser.error("Use --write to update files or --check to validate them.")

    changed = update_bread_report(write=args.write)
    if args.check and changed:
        print("Generated calibration report sections are stale. Run:")
        print("  uv run python scripts/update_calibration_reports.py --write")
        return 1
    if args.write and changed:
        print(f"Updated {BREAD_REPORT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
