"""Generate reproducible digital campaign reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from glutenix.analysis.campaigns import campaign_specs, planned_campaign_outputs


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "campaigns"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", choices=["all", *campaign_specs().keys()], default="all")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--date", dest="report_date", help="Report date slug, for example 2026-06-21")
    parser.add_argument("--check", action="store_true", help="Fail if generated campaign reports are stale")
    parser.add_argument("--dry-run", action="store_true", help="Use small sample counts and print planned outputs only")
    args = parser.parse_args()

    sample_mode = "dry-run" if args.dry_run else "default"
    outputs = planned_campaign_outputs(
        output_dir=args.output_dir,
        report_date=args.report_date,
        campaign=args.campaign,
        sample_mode=sample_mode,
    )

    if args.dry_run:
        for path, content in outputs.items():
            print(f"{path.relative_to(PROJECT_ROOT)}: {len(content.splitlines())} lines")
        return 0

    if args.check:
        stale = [path for path, content in outputs.items() if not path.exists() or path.read_text(encoding="utf-8") != content]
        if stale:
            print("Campaign reports are stale:")
            for path in stale:
                print(f"- {path.relative_to(PROJECT_ROOT)}")
            print("Run:")
            print("  uv run python scripts/run_digital_campaigns.py")
            return 1
        print("Campaign reports are up to date.")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
